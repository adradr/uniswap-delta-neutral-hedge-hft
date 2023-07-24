[Back to Main README](../README.md)

## uniswap_hft.scheduler

This script is designed to regularly run tasks (update a trading engine and retrieve its stats) at specified intervals. Here's a breakdown of its functionality:

---

### Imports:

1. **Built-in libraries**: 
   - `argparse`: Used for command-line argument parsing.
   - `logging`: Provides logging capabilities.
   - `os`: Interact with the OS, in this case for environment variables.
   - `time`: For sleep functionality.

2. **External libraries**:
   - `apscheduler`: Scheduling library to run tasks periodically.
   - `dotenv`: Reads .env files to set environment variables.
   - `requests`: Make HTTP requests.

### Configuration:

- **Environment Variables**: The script loads environment variables from a `.env` file using `dotenv`.
  
- **Logging**: Configured to display messages at `INFO` level and above.

- **Argument Parsing**: Command-line arguments can be passed to configure the script. If not provided, the script falls back to using environment variables. The following arguments can be provided:
  - `username`: For API authentication.
  - `password`: For API authentication.
  - `interval`: Time interval for scheduler (in seconds).
  - `api-host`: The API's host address.
  - `api-port`: The port on which the API is listening.

### Functions:

1. **get_auth_token(username, password)**:
   - Logs into an API and retrieves an authentication token.
   - If the login is successful and returns a 200 status code, the function returns the token. Otherwise, logs an error message and returns `None`.

2. **update_engine(token)**:
   - Uses the provided token to update the trading engine through the API.
   - Logs the outcome of the operation.

3. **get_stats(token)**:
   - Uses the provided token to retrieve stats about the trading engine through the API.
   - Logs the outcome of the operation.

4. **scheduler_job_update_engine()**:
   - Scheduled function that retrieves an auth token and then updates the trading engine.

5. **scheduler_job_get_stats()**:
   - Scheduled function that retrieves an auth token and then gets stats of the trading engine.

6. **main()**:
   - Sets up the scheduler with a `sqlite` job store and thread pool executor.
   - Schedules the above two functions to run at specified intervals.
   - Starts the scheduler and then enters an infinite loop, effectively running forever until interrupted.

### Execution:

- If the script is executed directly (not imported as a module), the `main` function is called.

### Use Case:

This script can be used in trading environments where there's a need to periodically update a trading engine and monitor its stats. For instance, this could be part of a high-frequency trading setup or any other trading setup where regular updates and monitoring are crucial. 

### Recommendations for Usage:

1. **Security**: Ensure that your `.env` file (which potentially contains sensitive credentials) is not included in version control or accessible by unauthorized users.
   
2. **Error Handling**: While there's basic error logging, you might want to add more robust error handling and potentially alerting mechanisms if certain actions fail.
   
3. **Scalability**: If you anticipate a lot of scheduled tasks or high concurrency needs, consider using more robust storage options than SQLite, and adjusting the ThreadPoolExecutor size accordingly. 

4. **HTTP Prefix**: Currently, the script uses `http://` as the prefix for API requests. If your API supports HTTPS, it's recommended to switch to `https://` for secure communications if the scheduler is accessing the API through a public network.