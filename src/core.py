from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd
from pathlib import Path

@dataclass
class EmissionResult:
    vehicle: str
    material: str
    co2e: float
    breakdown: Dict[str, float]

class EmissionCalculator:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self._load_data()
    
    def _load_data(self) -> None:
        """Load all database sheets from DB2.xlsx into memory."""
        try:
            # Load vehicle emissions from DB1
            self.vehicle_emissions = pd.read_excel(
                self.data_dir / "DB1_vehicle_emissions.xlsx"
            )
            
            # Load all other data from DB2.xlsx with different sheets
            db2_path = self.data_dir / "DB2.xlsx"
            
            # Load all sheets from DB2.xlsx
            self.materials = pd.read_excel(db2_path, sheet_name="Sheet1")
            self.waste_methods = pd.read_excel(db2_path, sheet_name="Sheet2")
            self.delivery_modes = pd.read_excel(db2_path, sheet_name="Sheet3")
            
            # Debug: Print available materials
            print("\nAvailable materials in Sheet1:")
            print(self.materials['Level 2'].dropna().unique())
            print(self.materials['Level 3'].dropna().unique())
            
        except FileNotFoundError as e:
            raise RuntimeError(f"Failed to load database files: {e}")

    def calculate_emissions(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        weight: float,
        material: str = "Cardboard"
    ) -> EmissionResult:
        """
        Calculate emissions for a shipment.
        
        Args:
            origin: Tuple of (latitude, longitude)
            destination: Tuple of (latitude, longitude)
            weight: Weight of shipment in kg
            material: Packaging material type
            
        Returns:
            EmissionResult object with calculated emissions
        """
        # Calculate distance using geopy
        from geopy.distance import geodesic
        distance = geodesic(origin, destination).kilometers

        # Find best vehicle based on distance and weight
        best_vehicle = self._select_best_vehicle(distance, weight)
        
        # Calculate transport emissions
        transport_emissions = self._calculate_transport_emissions(
            distance, weight, best_vehicle
        )
        
        # Calculate packaging emissions
        packaging_emissions = self._calculate_packaging_emissions(
            weight, material
        )
        
        # Calculate waste emissions
        waste_emissions = self._calculate_waste_emissions(
            weight, material
        )
        
        total_emissions = (
            transport_emissions +
            packaging_emissions +
            waste_emissions
        )
        
        return EmissionResult(
            vehicle=best_vehicle,
            material=material,
            co2e=total_emissions,
            breakdown={
                "transport": transport_emissions,
                "packaging": packaging_emissions,
                "waste": waste_emissions
            }
        )

    def _select_best_vehicle(self, distance: float, weight: float) -> str:
        """Select the most efficient vehicle based on distance and weight."""
        # Filter for delivery vehicles
        transport_vehicles = self.delivery_modes[
            self.delivery_modes['Level 1'].str.contains('Delivery', case=False, na=False)
        ]
        
        # Filter out WTT (Well-to-Tank) entries
        transport_vehicles = transport_vehicles[
            ~transport_vehicles['Level 2'].str.contains('WTT', na=False)
        ]
        
        if transport_vehicles.empty:
            raise ValueError("No delivery vehicles found in database")
        
        # Convert weight to tonnes for comparison
        weight_tonnes = weight / 1000  # Convert kg to tonnes
        
        # Filter vehicles by weight capacity
        valid_vehicles = transport_vehicles.copy()
        
        # For vans, filter by weight class
        van_mask = valid_vehicles['Level 2'] == 'Vans'
        if weight_tonnes <= 1.305:
            valid_vehicles = valid_vehicles[
                ~van_mask | (van_mask & valid_vehicles['Level 3'].str.contains('Class I', na=False))
            ]
        elif weight_tonnes <= 1.74:
            valid_vehicles = valid_vehicles[
                ~van_mask | (van_mask & valid_vehicles['Level 3'].str.contains('Class II', na=False))
            ]
        elif weight_tonnes <= 3.5:
            valid_vehicles = valid_vehicles[
                ~van_mask | (van_mask & valid_vehicles['Level 3'].str.contains('Class III', na=False))
            ]
        
        if valid_vehicles.empty:
            raise ValueError(f"No suitable vehicle found for weight: {weight} kg")
        
        # Convert GHG values to numeric, handling any non-numeric or missing values
        valid_vehicles['GHG_numeric'] = pd.to_numeric(
            valid_vehicles['GHG Conversion Factor 2024'],  # Using the 2024 conversion factor instead of GHG/Unit
            errors='coerce'
        ).fillna(float('inf'))
        
        # Select vehicle with lowest emissions
        best_vehicle = valid_vehicles.loc[valid_vehicles['GHG_numeric'].idxmin()]
        
        # Use Level 3 for vans (specific class), Level 2 for others
        if best_vehicle['Level 2'] == 'Vans':
            return best_vehicle['Level 3']
        return best_vehicle['Level 2']

    def _calculate_transport_emissions(
        self,
        distance: float,
        weight: float,
        vehicle: str
    ) -> float:
        """Calculate emissions from transport."""
        # Try to find the vehicle in Level 3 first, then Level 2
        vehicle_data = self.delivery_modes[
            (self.delivery_modes['Level 3'] == vehicle) | 
            (self.delivery_modes['Level 2'] == vehicle)
        ]
        
        if vehicle_data.empty:
            raise ValueError(f"Vehicle type '{vehicle}' not found in database")
        
        vehicle_data = vehicle_data.iloc[0]
        
        # Use the 2024 conversion factor instead of GHG/Unit
        ghg_per_unit = pd.to_numeric(vehicle_data['GHG Conversion Factor 2024'], errors='coerce')
        if pd.isna(ghg_per_unit):
            raise ValueError(f"Invalid GHG Conversion Factor for vehicle type '{vehicle}'")
        
        # Get the UOM to determine calculation method
        uom = str(vehicle_data['UOM']).lower()
        
        # Calculate emissions based on UOM
        if 'tonne.km' in uom:
            # Convert weight to tonnes
            weight_tonnes = weight / 1000
            return distance * ghg_per_unit * weight_tonnes
        elif 'km' in uom:
            # If the factor is per km, just multiply by distance
            return distance * ghg_per_unit
        else:
            # Default calculation
            return distance * ghg_per_unit * weight

    def _get_standardized_material(self, material: str) -> str:
        """Map common material names to database categories."""
        material_mapping = {
            'cardboard': 'Paper and board: board',
            'paper': 'Paper and board: paper',
            'mixed paper': 'Paper and board: mixed',
            'plastic': 'Plastics: average plastics',
            'plastic film': 'Plastics: average plastic film',
            'plastic rigid': 'Plastics: average plastic rigid',
            'metal': 'Metal: scrap metal',
            'aluminum': 'Metal: aluminium cans and foil (excl. forming)',
            'steel': 'Metal: steel cans',
            'glass': 'Glass',
            'wood': 'Wood'
        }
        
        # First try direct mapping
        material_lower = material.lower()
        if material_lower in material_mapping:
            return material_mapping[material_lower]
        
        # If not in mapping, return as is (might be using exact database name)
        return material

    def _calculate_packaging_emissions(
        self,
        weight: float,
        material: str
    ) -> float:
        """Calculate emissions from packaging."""
        # Get standardized material name
        std_material = self._get_standardized_material(material)
        
        # Find material in the materials sheet (Sheet1)
        material_data = self.materials[
            (self.materials['Level 2'].str.contains(std_material, case=False, na=False)) |
            (self.materials['Level 3'].str.contains(std_material, case=False, na=False))
        ]
        
        if material_data.empty:
            # If not found, show available options
            print("\nAvailable materials:")
            print("Level 2 categories:", self.materials['Level 2'].dropna().unique())
            print("\nLevel 3 categories:", self.materials['Level 3'].dropna().unique())
            raise ValueError(f"Material '{material}' (standardized as '{std_material}') not found in database")
        
        material_data = material_data.iloc[0]
        
        # Use GHG Conversion Factor 2024 for calculation
        ghg_factor = pd.to_numeric(material_data['GHG Conversion Factor 2024'], errors='coerce')
        if pd.isna(ghg_factor):
            raise ValueError(f"Invalid GHG Conversion Factor for material '{std_material}'")
        
        # Assume packaging weight is 10% of shipment weight
        packaging_weight = weight * 0.1
        
        # Check UOM to determine calculation method
        uom = str(material_data['UOM']).lower()
        if 'tonne' in uom:
            # Convert weight to tonnes
            packaging_weight = packaging_weight / 1000
        
        return packaging_weight * ghg_factor

    def _calculate_waste_emissions(
        self,
        weight: float,
        material: str
    ) -> float:
        """Calculate emissions from waste disposal."""
        # Get standardized material name
        std_material = self._get_standardized_material(material)
        
        # Find material in the materials sheet
        material_data = self.materials[
            (self.materials['Level 2'].str.contains(std_material, case=False, na=False)) |
            (self.materials['Level 3'].str.contains(std_material, case=False, na=False))
        ]
        
        if material_data.empty:
            raise ValueError(f"Material '{std_material}' not found in database")
        
        material_data = material_data.iloc[0]
        
        # Find waste disposal method in Sheet2
        # First, let's print available waste categories for debugging
        print("\nAvailable waste categories:")
        print("Level 1:", self.waste_methods['Level 1'].dropna().unique())
        print("Level 2:", self.waste_methods['Level 2'].dropna().unique())
        print("Level 3:", self.waste_methods['Level 3'].dropna().unique())
        
        # Try to find a matching waste category for paper/board
        waste_data = self.waste_methods[
            (self.waste_methods['Level 2'].str.contains('Paper', case=False, na=False)) |
            (self.waste_methods['Level 2'].str.contains('Board', case=False, na=False)) |
            (self.waste_methods['Level 3'].str.contains('Paper', case=False, na=False)) |
            (self.waste_methods['Level 3'].str.contains('Board', case=False, na=False))
        ]
        
        if waste_data.empty:
            # If no specific paper/board waste method found, try to find general recycling/waste
            waste_data = self.waste_methods[
                (self.waste_methods['Level 2'].str.contains('Waste', case=False, na=False)) |
                (self.waste_methods['Level 2'].str.contains('Disposal', case=False, na=False))
            ]
        
        if waste_data.empty:
            print("\nNo suitable waste disposal method found. Available methods:")
            print(self.waste_methods[['Level 1', 'Level 2', 'Level 3']].to_string())
            return 0  # Return 0 emissions if no suitable method found
        
        # Use the first matching waste method
        waste_data = waste_data.iloc[0]
        
        # Use GHG Conversion Factor 2024 for calculation
        ghg_factor = pd.to_numeric(waste_data['GHG Conversion Factor 2024'], errors='coerce')
        if pd.isna(ghg_factor):
            return 0  # Return 0 emissions if no valid conversion factor
        
        # Assume packaging weight is 10% of shipment weight
        packaging_weight = weight * 0.1
        
        # Check UOM to determine calculation method
        uom = str(waste_data['UOM']).lower()
        if 'tonne' in uom:
            # Convert weight to tonnes
            packaging_weight = packaging_weight / 1000
        
        return packaging_weight * ghg_factor
