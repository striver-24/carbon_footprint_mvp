from typing import Dict, List, Optional, Tuple
import re
import requests
from time import sleep
from .core import EmissionCalculator
from geopy.distance import geodesic

class RecommendationChatbot:
    def __init__(self):
        self.calculator = EmissionCalculator()
        self.conversation_state = {}
        
        # Define valid materials mapping
        self.materials_mapping = {
            '1': 'Paper and board: board',
            'cardboard': 'Paper and board: board',
            'board': 'Paper and board: board',
            '2': 'Plastics: average plastics',
            'plastic': 'Plastics: average plastics',
            '3': 'Paper and board: paper',
            'paper': 'Paper and board: paper',
            '4': 'Paper and board: mixed',
            'mixed': 'Paper and board: mixed',
            'mixed materials': 'Paper and board: mixed'
        }

    def initialize_conversation(self, session_id: str) -> str:
        """Initialize a new conversation."""
        self.conversation_state[session_id] = {
            'stage': 'welcome',
            'data': {},
            'origin': None,
            'destination': None,
            'weight': None,
            'material': None
        }
        return self.get_welcome_message()
    
    def get_welcome_message(self) -> str:
        return """Hello! 👋 I'm your Carbon Footprint Assistant. I can help you:
1. Calculate shipping emissions 📊
2. Find eco-friendly packaging options 📦
3. Get sustainability recommendations 🌱

Would you like to calculate emissions for a shipment? (yes/no)"""

    def handle_message(self, session_id: str, message: str) -> str:
        """Process user message and return appropriate response."""
        if session_id not in self.conversation_state:
            return self.initialize_conversation(session_id)
        
        state = self.conversation_state[session_id]
        message = message.strip()  # Don't convert to lowercase here
        
        if state['stage'] == 'welcome':
            if message.lower() in ['yes', 'y', 'sure', 'okay']:
                state['stage'] = 'origin'
                return "Great! Let's start with the origin location. Please enter a city name or coordinates (latitude,longitude):"
            else:
                return "I understand. When you're ready to calculate shipping emissions, just say 'start'."
        
        elif state['stage'] == 'origin':
            location = self._parse_location(message)
            if location:
                state['origin'] = location
                state['stage'] = 'destination'
                lat, lon = location
                return f"Perfect! I found the coordinates ({lat:.6f}, {lon:.6f}). Now, please provide the destination location (city name or coordinates):"
            else:
                return "I couldn't find that location. Please try entering a different city name or coordinates (like '51.5074,-0.1278'):"
        
        elif state['stage'] == 'destination':
            location = self._parse_location(message)
            if location:
                state['destination'] = location
                state['stage'] = 'weight'
                lat, lon = location
                return f"Great! I found the coordinates ({lat:.6f}, {lon:.6f}). How much does your shipment weigh (in kg)?"
            else:
                return "I couldn't find that location. Please try entering a different city name or coordinates (like '51.5074,-0.1278'):"
        
        elif state['stage'] == 'weight':
            try:
                weight = float(message.replace('kg', '').strip())
                if weight <= 0:
                    return "The weight must be greater than 0. Please enter a valid weight in kg:"
                state['weight'] = weight
                state['stage'] = 'material'
                return """What packaging material would you like to use? Choose from:
1. Cardboard (Paper Board)
2. Plastic
3. Paper
4. Mixed Materials

Enter the number or material name:"""
            except ValueError:
                return "Please enter a valid number for the weight in kg:"
        
        elif state['stage'] == 'material':
            # Handle material selection
            material_input = message.lower().strip()
            selected_material = self.materials_mapping.get(material_input)
            
            if selected_material:
                state['material'] = selected_material
                return self._calculate_and_respond(session_id)
            else:
                return """I didn't recognize that material. Please choose from:
1. Cardboard (Paper Board)
2. Plastic
3. Paper
4. Mixed Materials

Enter the number or material name:"""
        
        elif state['stage'] == 'calculation':
            if message.lower() in ['restart', 'new', 'start over']:
                return self.initialize_conversation(session_id)
            elif message.lower() in ['1', 'yes', 'calculate', 'another']:
                return self.initialize_conversation(session_id)
            elif message.lower() in ['2', 'recommendations', 'eco']:
                return self._get_eco_recommendations(state)
            elif message.lower() in ['3', 'end', 'quit', 'exit']:
                return "Thank you for using the Carbon Footprint Calculator! Have a great day! 👋"
            else:
                return """Please choose an option:
1. Calculate another shipment
2. Get eco-friendly recommendations
3. End conversation"""

    def _parse_location(self, location_str: str) -> Optional[Tuple[float, float]]:
        """Parse location string into coordinates."""
        # First, check if it's already in coordinate format
        coord_pattern = r'^(-?\d+\.?\d*),\s*(-?\d+\.?\d*)$'
        match = re.match(coord_pattern, location_str)
        if match:
            return (float(match.group(1)), float(match.group(2)))
        
        # If not coordinates, try to geocode the location name
        try:
            coordinates = self._geocode_location(location_str)
            if coordinates:
                return coordinates
        except Exception as e:
            print(f"Geocoding error: {e}")
            return None
        
        return None

    def _geocode_location(self, location_name: str) -> Optional[Tuple[float, float]]:
        """Convert location name to coordinates using Nominatim API."""
        # Add delay to respect Nominatim's usage policy
        sleep(1)
        
        try:
            # Construct the API URL
            base_url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': location_name,
                'format': 'json',
                'limit': 1,
                'accept-language': 'en'
            }
            
            # Add user agent to comply with Nominatim's usage policy
            headers = {
                'User-Agent': 'CarbonFootprintCalculator/1.0'
            }
            
            response = requests.get(base_url, params=params, headers=headers)
            response.raise_for_status()
            
            results = response.json()
            
            if results:
                # Get the first result
                location = results[0]
                return (float(location['lat']), float(location['lon']))
            
            return None

        except requests.exceptions.RequestException as e:
            print(f"Error during geocoding: {e}")
            return None
    
    def _calculate_and_respond(self, session_id: str) -> str:
        """Calculate emissions and provide recommendations."""
        state = self.conversation_state[session_id]
        try:
            # Ensure all required data is present
            if not all(key in state and state[key] is not None 
                      for key in ['origin', 'destination', 'weight', 'material']):
                raise ValueError("Missing required information for calculation")

            # Calculate distance
            distance = geodesic(state['origin'], state['destination']).kilometers
            
            # Calculate time (assuming average speed of 60 km/h)
            time_hours = distance / 60
            hours = int(time_hours)
            minutes = int((time_hours - hours) * 60)

            result = self.calculator.calculate_emissions(
                origin=state['origin'],
                destination=state['destination'],
                weight=state['weight'],
                material=state['material']
            )
            
            # Format the response
            response = f"""📊 Emission Calculation Results:

📍 Route Information:
   • Distance: {distance:.2f} km
   • Estimated Time: {hours}h {minutes}m

🚛 Recommended Vehicle: {result.vehicle}
📦 Packaging Material: {result.material}
🌱 Total CO₂e: {result.co2e:.2f} kg

Breakdown:
🚗 Transport: {result.breakdown['transport']:.2f} kg CO₂e
📦 Packaging: {result.breakdown['packaging']:.2f} kg CO₂e
♻️ Waste: {result.breakdown['waste']:.2f} kg CO₂e

Would you like to:
1. Calculate another shipment
2. Get eco-friendly recommendations
3. End conversation"""
            
            state['stage'] = 'calculation'
            return response
            
        except Exception as e:
            print(f"Calculation error: {e}")  # For debugging
            return f"I encountered an error while calculating: {str(e)}\nWould you like to try again? (yes/no)"

    def _get_eco_recommendations(self, state: Dict) -> str:
        """Provide eco-friendly recommendations based on the calculation."""
        return """🌱 Eco-Friendly Recommendations:

1. Packaging Tips:
   • Use recycled cardboard when possible
   • Minimize void space in packages
   • Choose appropriate box sizes

2. Transport Options:
   • Consider consolidating shipments
   • Use electric vehicles for short distances
   • Plan routes efficiently

3. General Tips:
   • Track and offset carbon emissions
   • Use local distribution centers
   • Implement reverse logistics

Would you like to:
1. Calculate another shipment
2. End conversation"""
