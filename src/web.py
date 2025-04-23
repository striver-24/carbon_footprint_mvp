from flask import Flask, render_template, request, jsonify, session
from .core import EmissionCalculator
from .chatbot import RecommendationChatbot
import uuid

app = Flask(__name__)
# Add a secret key for session management
app.secret_key = 'your-super-secret-key-here'  # In production, use a secure random key

# Initialize calculator and chatbot
calculator = EmissionCalculator()
chatbot = RecommendationChatbot()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        
        # Get box dimensions if provided
        box_dimensions = data.get('box_dimensions')
        
        # Calculate emissions using multi-modal route
        result = calculator.calculate_multi_modal_emissions(
            route_segments=data['segments'],
            weight=float(data['weight']),
            material=data['material'],
            box_dimensions=box_dimensions
        )

        # Format response
        response = {
            'success': True,
            'segments': [
                {
                    'mode': segment.mode,
                    'vehicle': segment.vehicle,
                    'distance': round(segment.distance, 2),
                    'emissions': round(segment.emissions, 2)
                }
                for segment in result.segments
            ],
            'material': result.material,
            'co2e': round(result.co2e, 2),
            'breakdown': {
                k: round(v, 2) for k, v in result.breakdown.items()
            },
            'total_distance': round(result.total_distance, 2),
            'total_time': round(result.total_time, 2)
        }
        
        # Add loading capacity information if box dimensions were provided
        if result.box_info:
            response['loading_info'] = {
                vehicle: {
                    'total_boxes': info.total_boxes,
                    'rows': info.rows,
                    'columns': info.columns,
                    'layers': info.layers,
                    'utilization_percentage': info.utilization_percentage,
                    'remaining_space': round(info.remaining_space, 3)
                }
                for vehicle, info in result.loading_info.items()
            }
        
        return jsonify(response)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/chat', methods=['GET'])
def chat_interface():
    """Render chat interface."""
    return render_template('chat.html')

@app.route('/chat/message', methods=['POST'])
def chat_message():
    """Handle chat messages."""
    data = request.json
    message = data.get('message', '').strip()
    
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    response = chatbot.handle_message(session['session_id'], message)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True)
