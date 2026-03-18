"""Azure Function — Fee Alert Timer Trigger.

Runs every 60 seconds, checks fee alerts and tx watches, fires matching webhooks.
This is a thin wrapper around the portable fee_alert_worker.py logic.

Deploy: func azure functionapp publish <app-name>
Local:  func start
"""

import logging
import os
import sys

import azure.functions as func

# Add parent directories so we can import the worker
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

app = func.FunctionApp()


@app.timer_trigger(schedule="0 * * * * *", arg_name="timer", run_on_startup=False)
def fee_alert_timer(timer: func.TimerRequest) -> None:
    """Run fee alert + tx watch checks every 60 seconds."""
    logging.info("Fee alert timer triggered")

    try:
        from fee_alert_worker import get_db, process_fee_alerts, process_tx_watches

        db = get_db()
        try:
            process_fee_alerts(db)
            process_tx_watches(db)
        finally:
            db.close()

        logging.info("Fee alert check completed")
    except Exception:
        logging.exception("Fee alert worker failed")
