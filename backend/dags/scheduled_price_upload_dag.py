"""
Airflow DAG: Scheduled Price Upload

ตรวจสอบและประมวลผลไฟล์ราคาที่กำหนดวันที่อัพโหลด
รันทุกวันเวลา 00:00 เพื่อตรวจสอบไฟล์ที่ถึงกำหนด
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# Import job function
from jobs.scheduled_price_upload_fully_standalone import run_scheduled_price_upload


# ============================================
# Default DAG settings
# ============================================
default_args = {
    "owner": "supplysense",
    "depends_on_past": False,
    "start_date": datetime(2026, 5, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


# ============================================
# DAG Definition
# ============================================
with DAG(
    dag_id="scheduled_price_upload",
    description="Process scheduled price upload files daily",
    default_args=default_args,
    schedule_interval="0 0 * * *",  # รันทุกวันเวลา 00:00 (เที่ยงคืน)
    catchup=False,
    tags=["price", "upload", "scheduled"],
) as dag:

    def run_scheduled_price_job():
        """Run scheduled price upload job"""
        result = run_scheduled_price_upload()

        # Log summary
        print("=" * 80)
        print("SCHEDULED PRICE UPLOAD RESULT:")
        print("=" * 80)
        print(f"Duration: {result.duration_seconds:.2f} seconds")
        print(f"Files Found: {result.files_found}")
        print(f"Files Processed: {result.files_processed}")
        print(f"Files Failed: {result.files_failed}")
        print(f"Total Items Uploaded: {result.total_items_uploaded}")
        print("=" * 80)

        # Raise exception if there are errors
        if result.errors:
            error_msg = f"Job finished with {len(result.errors)} error(s)"
            print(f"❌ {error_msg}")
            for error in result.errors:
                print(f"  - {error}")
            raise Exception(error_msg)
        
        print("✅ Scheduled price upload completed successfully")
        
        return {
            "files_found": result.files_found,
            "files_processed": result.files_processed,
            "files_failed": result.files_failed,
            "total_items_uploaded": result.total_items_uploaded,
            "duration_seconds": result.duration_seconds
        }

    # Task: Run scheduled price upload job
    run_job = PythonOperator(
        task_id="run_scheduled_price_upload",
        python_callable=run_scheduled_price_job,
        execution_timeout=timedelta(minutes=15),
    )

    run_job
