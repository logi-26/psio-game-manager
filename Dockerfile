FROM python:3.9-slim

# Copy the requirements.txt file into the container
COPY requirements.txt /home/

# Install dependencies
RUN pip install -r /home/requirements.txt

# Create the src directory
RUN mkdir -p /home/src

# Copy the rest of the application code to the home directory
COPY src/* /home/src/

# Set the src directory as the working directory
WORKDIR /home/src/

# Specify the command to run the application
CMD ["python", "psio_assist.py"]