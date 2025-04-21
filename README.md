# Carbon Footprint Calculator for E-commerce Logistics

An AI-powered system that calculates and recommends lowest-emission shipping options for e-commerce logistics. This MVP (Minimum Viable Product) helps businesses make environmentally conscious decisions about their shipping and packaging choices.

## 🌟 Features

### Current Features
- ✅ Smart vehicle selection based on distance and load
- ✅ Accurate emissions calculation for transport
- ✅ Packaging material impact assessment
- ✅ Waste disposal emissions evaluation
- ✅ User-friendly CLI with colored output

### Upcoming Features
- 🚧 Multi-modal transport analysis (road, air, sea)
- 🚧 Real-time route optimization
- 🚧 Interactive chatbot interface
- 🚧 Web API for system integration

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- pip package manager
- Virtual environment (recommended)

### Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/carbon_footprint_mvp.git
cd carbon_footprint_mvp
```

2. Create and activate a virtual environment:
```bash
# On macOS/Linux
python -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## 💻 Usage

### Command Line Interface

Calculate emissions for a shipment using the CLI:

```bash
python -m src.cli --origin "51.5074,-0.1278" \
                 --destination "48.8566,2.3522" \
                 --weight 100 \
                 --material "Cardboard"
```

#### Parameters:
- `--origin`: Starting point coordinates (latitude,longitude)
- `--destination`: Delivery point coordinates (latitude,longitude)
- `--weight`: Shipment weight in kilograms
- `--material`: Packaging material (default: "Cardboard")

### Example Output

```
┌─────────────────────────────────┐
│    Carbon Footprint Analysis    │
├───────────────────┬─────────────┤
│ Category          │ Value       │
├───────────────────┼─────────────┤
│ Recommended Vehicle│ Electric Van│
│ Packaging Material│ Cardboard   │
│ Total CO₂e (kg)   │ 24.76      │
├───────────────────┼─────────────┤
│ Transport Emissions│ 20.10 kg CO₂e│
│ Packaging Emissions│ 4.50 kg CO₂e │
│ Waste Emissions    │ 0.16 kg CO₂e │
└───────────────────┴─────────────┘
```

## 📊 Data Structure

The system uses a combination of databases to calculate emissions:

1. **Vehicle Emissions** (DB1_vehicle_emissions.xlsx)
   - Vehicle types and their emission factors
   - Fuel efficiency data
   - Capacity constraints

2. **Delivery Modes** (DB2.xlsx)
   - Transport modes and specifications
   - Materials database
   - Waste disposal methods

## 🛠️ Technical Details

### Core Components
- `src/core.py`: Main calculation engine
- `src/cli.py`: Command-line interface
- `data/`: Database files

### Dependencies
- pandas (1.5.3): Data processing
- openpyxl (3.0.10): Excel file handling
- geopy (2.3.0): Distance calculations
- click (8.1.3): CLI interface
- rich (13.3.1): Terminal formatting

## 🤝 Contributing

Contributions are welcome! Here are some ways you can contribute:
1. Report bugs
2. Suggest new features
3. Submit pull requests

Please read our contributing guidelines before submitting pull requests.

## 📝 TODO

- [ ] Implement multi-modal transport analysis
- [ ] Add OSRM integration for better route optimization
- [ ] Create web API interface
- [ ] Add comprehensive unit tests
- [ ] Implement caching for frequent calculations
- [ ] Add more vehicle and material options

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Authors

- Your Name (@yourusername)

## 🙏 Acknowledgments

- Thanks to all contributors who have helped shape this project
- Special thanks to the open-source community for providing excellent tools and libraries

---

For more information or support, please open an issue in the GitHub repository.