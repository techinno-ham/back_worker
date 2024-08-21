import asyncio
import random

async def process_job(job_id: int):
    # Simulate job processing time with a random sleep
    processing_time = random.uniform(1, 3)
    await asyncio.sleep(processing_time)
    print(f"Job {job_id} processed in {processing_time:.2f} seconds")

async def job_worker(queue: asyncio.Queue):
    while True:
        job_id = await queue.get()  # Wait for a job from the queue
        if job_id is None:
            # If None is received, break the loop and stop the worker
            break
        print(f"Worker started processing job {job_id}")
        asyncio.create_task(process_job(job_id))  # Process the job asynchronously
        queue.task_done()

async def main():
    queue = asyncio.Queue()

    # Start the worker
    worker_task = asyncio.create_task(job_worker(queue))

    # Simulate adding jobs to the queue
    for job_id in range(10):
        print(f"Adding job {job_id} to the queue")
        await queue.put(job_id)
        await asyncio.sleep(0.5)  # Simulate some delay between job arrivals

    # Wait for all jobs to be processed
    await queue.join()

    # Stop the worker by sending None to the queue
    await queue.put(None)
    await worker_task  # Wait for the worker to finish

if __name__ == "__main__":
    asyncio.run(main())
