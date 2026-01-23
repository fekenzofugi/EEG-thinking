import os
from multiprocessing import Process
import gunicorn
from app.run import app  # Import the Flask app from app/run.py

if __name__ == "__main__":
    # Initialize the database (if needed)
    # os.system('flask db init')
    # os.system('flask db migrate -m "Initial migration."')
    # os.system('flask db upgrade')

    # Start Flask app using Gunicorn in a separate process
    flask_process = Process(target=app.run, kwargs={"host": "localhost", "port": 5000, "debug": True})    # Start the processes
    flask_process.start()
    # Wait for the processes to complete
    flask_process.join()