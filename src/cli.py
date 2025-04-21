import click
from rich.console import Console
from rich.table import Table
from .core import EmissionCalculator

console = Console()

@click.command()
@click.option('--origin', required=True, help='Origin coordinates (lat,lon)')
@click.option('--destination', required=True, help='Destination coordinates (lat,lon)')
@click.option('--weight', required=True, type=float, help='Shipment weight in kg')
@click.option('--material', default='Cardboard', help='Packaging material')
def calculate(origin: str, destination: str, weight: float, material: str):
    """Calculate carbon emissions for a shipment."""
    try:
        # Parse coordinates
        origin_coords = tuple(map(float, origin.split(',')))
        dest_coords = tuple(map(float, destination.split(',')))
        
        calculator = EmissionCalculator()
        result = calculator.calculate_emissions(
            origin_coords,
            dest_coords,
            weight,
            material
        )
        
        # Create rich table for output
        table = Table(title="Carbon Footprint Analysis")
        
        table.add_column("Category", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Recommended Vehicle", result.vehicle)
        table.add_row("Packaging Material", result.material)
        table.add_row("Total CO₂e (kg)", f"{result.co2e:.2f}")
        
        # Add breakdown
        table.add_section()
        for category, value in result.breakdown.items():
            table.add_row(
                f"{category.title()} Emissions",
                f"{value:.2f} kg CO₂e"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")

if __name__ == '__main__':
    calculate()
