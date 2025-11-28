# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY backend/ .

# Make port 8080 available to the world outside this container
EXPOSE 8080

# The CMD below is what runs your Cloud Function.
# The --source flag points to the Python file containing your function.
# The --target flag is the name of the function to be executed.
# The --port flag specifies the port the server will listen on.
#
# For Cloud Run, the PORT environment variable is automatically set.
# The functions-framework will automatically use this PORT.
# You can override it with the --port flag.
CMD ["functions-framework", "--source=main.py", "--target=analyze_file"]
