#!/usr/bin/env python
import os
import subprocess
import sys
import click

# Always run commands relative to the backend directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

@click.group()
def cli():
    """NC Prediction Project Management Utility."""
    pass

@cli.command()
@click.option('--port', default=8000, help='Port to run the server on.')
@click.option('--reload/--no-reload', default=True, help='Reload server on code changes.')
def run(port, reload):
    """Start the FastAPI development server."""
    click.echo(f"Starting FastAPI development server on port {port} (reload={reload})...")
    cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)]
    if reload:
        cmd.append("--reload")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        click.echo("\nServer stopped.")

@cli.command()
def test():
    """Run backend integration tests."""
    click.echo("Running integration tests...")
    cmd = [sys.executable, "test_api.py"]
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

@cli.command()
def seed():
    """Seed the database with default configs and historical order data."""
    click.echo("Seeding database...")
    cmd = [sys.executable, "seed.py"]
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

@cli.command(name="reset-db")
def reset_db():
    """Reset the database file and re-seed metadata."""
    click.echo("Resetting database...")
    db_file = "nc_prediction.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            click.echo(f"Deleted database file '{db_file}'.")
        except Exception as e:
            click.echo(f"Error deleting database: {e}")
            sys.exit(1)
    else:
        click.echo("Database file not found. Initializing new database.")
    
    # Run seed script to recreate and populate
    cmd = [sys.executable, "seed.py"]
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

if __name__ == "__main__":
    cli()
