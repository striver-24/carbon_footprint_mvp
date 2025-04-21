# Carbon Footprint MVP

An AI-powered carbon footprint recommendation system for e-commerce logistics.

## Features

- Multi-modal transport analysis (road, air, sea)
- Packaging material impact assessment
- Waste disposal method evaluation
- Real-time distance calculations
- User-friendly CLI interface

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Use the CLI interface to calculate emissions:

```bash
python -m src.cli --origin "51.5074,-0.1278" \
                 --destination "48.8566,2.3522" \
                 --weight 100 \
                 --material "Cardboard"
```

## Database Structure

The system uses four Excel databases:
1. DB1_vehicle_emissions.xlsx - Vehicle emission factors
2. DB2_delivery_vehicles.xlsx - Delivery mode specifications
3. DB3_materials.xlsx - Packaging material properties
4. DB4_waste.xlsx - Waste disposal methods

## Example Output

```json
{
  "recommendation": {
    "vehicle": "Electric Van",
    "material": "Cardboard",
    "co2e": 24.76,
    "breakdown": {
      "transport": 20.1,
      "packaging": 4.5,
      "waste": 0.16
    }
  }
}
```
```

Now you need to create or update the Excel database files in the data directory. I notice you already have some files, but they might need to be updated to match the required schema. Would you like me to help you create or update these database files with the specified structure?

Also, would you like me to:
1. Add unit tests
2. Add more detailed documentation
3. Implement additional features like caching or API integration

Please let me know what aspects you'd like to focus on next!