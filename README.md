# ExpoScan Take-Home Anubhaw Kumar Gupta

## How to run
1. Clone the repository and navigate into the project directory.
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
4. Install the required dependencies: `pip install -r requirements.txt`
5. Create a `.env` file in the root directory and add your MongoDB connection string: `MONGODB_URI=your_mongodb_connection_string_here`
6. Start the FastAPI server: `uvicorn main:app --reload`
7. The API will be available at `http://127.0.0.1:8000/leads`.

## Driver choice
I used motor because FastAPI is built on an asynchronous architecture. Using the synchronous pymongo driver would block the event loop during database operations, defeating the performance benefits of FastAPI. Motor provides non-blocking, async/await compatibility that keeps the endpoint highly performant under load.

## How I handled idempotency
I created a dedicated `idempotency_keys` collection in MongoDB. When a request arrives, the endpoint first checks this collection for the provided `Idempotency-Key` header. If the key exists, the system bypasses the creation logic, fetches the original lead document, and returns it with a 200 OK status. If the key does not exist, the system creates the lead and atomically inserts the key to prevent future duplicates.

## Tradeoffs / what I'd do with more time
1. TTL Indexes: Add a Time-To-Live index to the `idempotency_keys` collection so keys automatically expire after 24 to 48 hours, preventing infinite storage growth.
2. Automated Testing: Write a robust test suite using pytest and httpx to automate the idempotency and payload validation checks.
3. Global Exception Handling: Implement custom FastAPI exception handlers to ensure any database timeouts or connection drops return sanitized, standard JSON error responses.
