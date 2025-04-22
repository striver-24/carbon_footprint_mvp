from flask import Flask, render_template, request, jsonify
from .core import EmissionCalculator

app = Flask(__name__)
calculator = EmissionCalculator()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        # Get data from request
        data = request.json
        origin = tuple(map(float, data['origin'].split(',')))
        destination = tuple(map(float, data['destination'].split(',')))
        weight = float(data['weight'])
        material = data['material']

        # Calculate emissions
        result = calculator.calculate_emissions(
            origin=origin,
            destination=destination,
            weight=weight,
            material=material
        )

        # Format response
        response = {
            'success': True,
            'vehicle': result.vehicle,
            'material': result.material,
            'co2e': round(result.co2e, 2),
            'breakdown': {
                k: round(v, 2) for k, v in result.breakdown.items()
            }
        }
        return jsonify(response)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

if __name__ == '__main__':
    app.run(debug=True)
