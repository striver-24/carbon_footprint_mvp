from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
from pathlib import Path
from geopy.distance import geodesic

@dataclass
class TransportSegment:
    mode: str
    vehicle: str
    distance: float
    emissions: float

@dataclass
class BoxDimensions:
    length: float  # in meters
    width: float   # in meters
    height: float  # in meters
    volume: float  # in cubic meters

@dataclass
class LoadingCapacity:
    total_boxes: int
    rows: int
    columns: int
    layers: int
    utilization_percentage: float
    remaining_space: float

@dataclass
class EmissionResult:
    segments: List[TransportSegment]
    material: str
    co2e: float
    breakdown: Dict[str, float]
    total_distance: float
    total_time: float
    box_info: BoxDimensions
    loading_info: Dict[str, LoadingCapacity]  # vehicle type -> loading capacity

@dataclass
class RouteOption:
    name: str
    description: str
    segments: List[Dict]
    total_time: float
    total_distance: float
    estimated_emissions: float
    cost_factor: float  # Relative cost (1.0 = standard)

class EmissionCalculator:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self._load_data()
        
        # Standard container/vehicle dimensions in meters
        self.vehicle_dimensions = {
            'Van - Class I': {'length': 2.5, 'width': 1.7, 'height': 1.4},
            'Van - Class II': {'length': 3.0, 'width': 1.8, 'height': 1.6},
            'Van - Class III': {'length': 4.0, 'width': 2.0, 'height': 1.8},
            'Truck - Small': {'length': 6.0, 'width': 2.4, 'height': 2.4},
            'Truck - Medium': {'length': 8.0, 'width': 2.4, 'height': 2.6},
            'Truck - Large': {'length': 13.6, 'width': 2.4, 'height': 2.7},
            'Container - 20ft': {'length': 5.9, 'width': 2.35, 'height': 2.39},
            'Container - 40ft': {'length': 12.0, 'width': 2.35, 'height': 2.39},
            'Aircraft Container': {'length': 3.17, 'width': 2.23, 'height': 2.23}
        }
        
        # Define mode characteristics
        self.mode_characteristics = {
            'road': {
                'speed': 60,      # km/h
                'cost_factor': 1.0,
                'emission_factor': 1.0
            },
            'rail': {
                'speed': 80,      # km/h
                'cost_factor': 0.8,
                'emission_factor': 0.4
            },
            'sea': {
                'speed': 30,      # km/h
                'cost_factor': 0.6,
                'emission_factor': 0.2
            },
            'air': {
                'speed': 800,     # km/h
                'cost_factor': 2.5,
                'emission_factor': 2.8
            }
        }
    
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

    def calculate_box_loading(
        self,
        box_dimensions: BoxDimensions,
        vehicle_type: str
    ) -> LoadingCapacity:
        """Calculate how many boxes can fit in the vehicle."""
        vehicle_dim = self.vehicle_dimensions[vehicle_type]
        
        # Calculate maximum number of boxes that can fit in each dimension
        rows = int(vehicle_dim['width'] / box_dimensions.width)
        columns = int(vehicle_dim['length'] / box_dimensions.length)
        layers = int(vehicle_dim['height'] / box_dimensions.height)
        
        # Calculate total boxes
        total_boxes = rows * columns * layers
        
        # Calculate space utilization
        vehicle_volume = vehicle_dim['length'] * vehicle_dim['width'] * vehicle_dim['height']
        total_box_volume = total_boxes * box_dimensions.volume
        utilization = (total_box_volume / vehicle_volume) * 100
        remaining_space = vehicle_volume - total_box_volume
        
        return LoadingCapacity(
            total_boxes=total_boxes,
            rows=rows,
            columns=columns,
            layers=layers,
            utilization_percentage=utilization,
            remaining_space=remaining_space
        )

    def calculate_multi_modal_emissions(
        self,
        route_segments: List[Dict],
        weight: float,
        material: str = "Paper and board: board",
        box_dimensions: Optional[Dict] = None
    ) -> EmissionResult:
        """
        Calculate emissions for a multi-modal journey.
        
        Args:
            route_segments: List of dictionaries containing:
                {
                    'origin': (lat, lon),
                    'destination': (lat, lon),
                    'mode': 'road'|'sea'|'air'|'rail'
                }
            weight: Weight of shipment in kg
            material: Packaging material type
            box_dimensions: Optional dictionary containing box dimensions in cm
        """
        total_emissions = 0
        total_distance = 0
        total_time = 0
        segments = []

        # Calculate emissions for each segment
        for segment in route_segments:
            # Calculate segment distance
            distance = geodesic(segment['origin'], segment['destination']).kilometers
            total_distance += distance

            # Select best vehicle for this segment based on mode and distance
            vehicle = self._select_best_vehicle(
                distance=distance,
                weight=weight,
                mode=segment['mode']
            )

            # Calculate segment emissions
            segment_emissions = self._calculate_transport_emissions(
                distance=distance,
                weight=weight,
                vehicle=vehicle,
                mode=segment['mode']
            )

            # Calculate estimated time for segment
            time = self._calculate_segment_time(distance, segment['mode'])
            total_time += time

            # Add segment to results
            segments.append(TransportSegment(
                mode=segment['mode'],
                vehicle=vehicle,
                distance=distance,
                emissions=segment_emissions
            ))

            total_emissions += segment_emissions

        # Calculate packaging and waste emissions
        packaging_emissions = self._calculate_packaging_emissions(weight, material)
        waste_emissions = self._calculate_waste_emissions(weight, material)

        # Calculate box information if dimensions provided
        box_info = None
        loading_info = {}
        
        if box_dimensions:
            # Convert dimensions to meters if provided in cm
            length_m = box_dimensions['length'] / 100
            width_m = box_dimensions['width'] / 100
            height_m = box_dimensions['height'] / 100
            volume = length_m * width_m * height_m
            
            box_info = BoxDimensions(
                length=length_m,
                width=width_m,
                height=height_m,
                volume=volume
            )
            
            # Calculate loading capacity for each vehicle type used
            for segment in segments:
                loading_info[segment.vehicle] = self.calculate_box_loading(
                    box_info, segment.vehicle
                )

        return EmissionResult(
            segments=segments,
            material=material,
            co2e=total_emissions + packaging_emissions + waste_emissions,
            breakdown={
                "transport": total_emissions,
                "packaging": packaging_emissions,
                "waste": waste_emissions
            },
            total_distance=total_distance,
            total_time=total_time,
            box_info=box_info,
            loading_info=loading_info
        )

    def _select_best_vehicle(
        self,
        distance: float,
        weight: float,
        mode: str
    ) -> str:
        """Select the most efficient vehicle based on mode, distance and weight."""
        # Filter for vehicles of the specified mode
        mode_mapping = {
            'road': 'Road',
            'sea': 'Water',
            'air': 'Air',
            'rail': 'Rail'
        }

        transport_vehicles = self.delivery_modes[
            self.delivery_modes['Level 1'].str.contains(mode_mapping[mode], case=False, na=False)
        ]

        if transport_vehicles.empty:
            raise ValueError(f"No vehicles found for mode: {mode}")

        # Convert weight to tonnes for comparison
        weight_tonnes = weight / 1000

        # Filter vehicles by weight capacity
        valid_vehicles = transport_vehicles.copy()

        # Select vehicle with lowest emissions
        valid_vehicles['GHG_numeric'] = pd.to_numeric(
            valid_vehicles['GHG Conversion Factor 2024'],
            errors='coerce'
        ).fillna(float('inf'))

        best_vehicle = valid_vehicles.loc[valid_vehicles['GHG_numeric'].idxmin()]
        
        return best_vehicle['Level 2']

    def _calculate_segment_time(self, distance: float, mode: str) -> float:
        """Calculate estimated time for segment in hours."""
        # Average speeds in km/h
        speeds = {
            'road': 60,  # Truck average speed
            'rail': 80,  # Train average speed
            'sea': 30,   # Ship average speed
            'air': 800   # Plane average speed
        }
        return distance / speeds[mode]

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

    def generate_route_options(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        weight: float
    ) -> Dict[str, RouteOption]:
        """Generate three route options: Eco, Standard, and Express."""
        distance = geodesic(origin, destination).kilometers
        
        # Generate different routing options based on distance
        options = {
            'eco': self._generate_eco_route(origin, destination, distance),
            'standard': self._generate_standard_route(origin, destination, distance),
            'express': self._generate_express_route(origin, destination, distance)
        }
        
        return options

    def _generate_eco_route(self, origin, destination, distance):
        """Generate the most eco-friendly route."""
        segments = []
        
        if distance < 800:
            # Short distance: Prefer rail or road
            segments.append({
                'mode': 'rail',
                'origin': origin,
                'destination': destination,
                'description': 'Direct rail transport'
            })
        else:
            # Long distance: Combine sea and rail/road
            midpoint = self._calculate_midpoint(origin, destination)
            segments.extend([
                {
                    'mode': 'road',
                    'origin': origin,
                    'destination': self._find_nearest_port(origin),
                    'description': 'Road transport to port'
                },
                {
                    'mode': 'sea',
                    'origin': self._find_nearest_port(origin),
                    'destination': self._find_nearest_port(destination),
                    'description': 'Sea freight'
                },
                {
                    'mode': 'road',
                    'origin': self._find_nearest_port(destination),
                    'destination': destination,
                    'description': 'Road transport from port'
                }
            ])
        
        return RouteOption(
            name="Eco-Friendly Route",
            description="Optimized for lowest emissions using rail and sea transport",
            segments=segments,
            total_time=self._calculate_route_time(segments),
            total_distance=self._calculate_route_distance(segments),
            estimated_emissions=self._estimate_route_emissions(segments),
            cost_factor=0.8
        )

    def _generate_standard_route(self, origin, destination, distance):
        """Generate a balanced route."""
        segments = []
        
        if distance < 500:
            # Short distance: Direct road transport
            segments.append({
                'mode': 'road',
                'origin': origin,
                'destination': destination,
                'description': 'Direct road transport'
            })
        else:
            # Long distance: Combine rail and road
            midpoint = self._calculate_midpoint(origin, destination)
            segments.extend([
                {
                    'mode': 'road',
                    'origin': origin,
                    'destination': midpoint,
                    'description': 'Road transport first leg'
                },
                {
                    'mode': 'rail',
                    'origin': midpoint,
                    'destination': destination,
                    'description': 'Rail transport second leg'
                }
            ])
        
        return RouteOption(
            name="Standard Route",
            description="Balanced option using road and rail transport",
            segments=segments,
            total_time=self._calculate_route_time(segments),
            total_distance=self._calculate_route_distance(segments),
            estimated_emissions=self._estimate_route_emissions(segments),
            cost_factor=1.0
        )

    def _generate_express_route(self, origin, destination, distance):
        """Generate the fastest route."""
        segments = []
        
        if distance < 300:
            # Short distance: Direct road transport
            segments.append({
                'mode': 'road',
                'origin': origin,
                'destination': destination,
                'description': 'Express road transport'
            })
        else:
            # Long distance: Air transport
            segments.extend([
                {
                    'mode': 'road',
                    'origin': origin,
                    'destination': self._find_nearest_airport(origin),
                    'description': 'Road transport to airport'
                },
                {
                    'mode': 'air',
                    'origin': self._find_nearest_airport(origin),
                    'destination': self._find_nearest_airport(destination),
                    'description': 'Air freight'
                },
                {
                    'mode': 'road',
                    'origin': self._find_nearest_airport(destination),
                    'destination': destination,
                    'description': 'Road transport from airport'
                }
            ])
        
        return RouteOption(
            name="Express Route",
            description="Fastest option using air transport for long distances",
            segments=segments,
            total_time=self._calculate_route_time(segments),
            total_distance=self._calculate_route_distance(segments),
            estimated_emissions=self._estimate_route_emissions(segments),
            cost_factor=2.5
        )

    # Helper methods
    def _calculate_midpoint(self, point1, point2):
        """Calculate the midpoint between two coordinates."""
        return (
            (point1[0] + point2[0]) / 2,
            (point1[1] + point2[1]) / 2
        )

    def _calculate_route_time(self, segments):
        """Calculate total route time in hours."""
        total_time = 0
        for segment in segments:
            distance = geodesic(segment['origin'], segment['destination']).kilometers
            speed = self.mode_characteristics[segment['mode']]['speed']
            total_time += distance / speed
        return total_time

    def _calculate_route_distance(self, segments):
        """Calculate total route distance in kilometers."""
        total_distance = 0
        for segment in segments:
            distance = geodesic(segment['origin'], segment['destination']).kilometers
            total_distance += distance
        return total_distance

    def _estimate_route_emissions(self, segments):
        """Estimate route emissions (relative units)."""
        total_emissions = 0
        for segment in segments:
            distance = geodesic(segment['origin'], segment['destination']).kilometers
            emission_factor = self.mode_characteristics[segment['mode']]['emission_factor']
            total_emissions += distance * emission_factor
        return total_emissions

    def _find_nearest_port(self, location):
        # Implementation of _find_nearest_port method
        pass

    def _find_nearest_airport(self, location):
        # Implementation of _find_nearest_airport method
        pass
