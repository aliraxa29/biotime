# Copyright (c) 2024, Ali Raxa and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BioTimeSettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        auth_token: DF.Password | None
        auth_token_type: DF.Literal["JWT", "General"]
        auto_map_employees: DF.Check
        block_new_registrations: DF.Check
        connection_status: DF.Data | None
        create_employee_checkin: DF.Check
        default_log_type: DF.Literal["", "IN", "OUT"]
        default_user: DF.Link | None
        employee_id_field: DF.Literal["Attendance Device ID", "Employee ID", "Employee Name"]
        enable_auto_sync: DF.Check
        last_sync_time: DF.Datetime | None
        last_transaction_sync: DF.Datetime | None
        log_retention_days: DF.Int
        password: DF.Password
        pull_areas: DF.Check
        pull_departments: DF.Check
        pull_devices: DF.Check
        pull_employees: DF.Check
        pull_positions: DF.Check
        server_url: DF.Data
        sync_days_back: DF.Int
        sync_interval_minutes: DF.Int
        username: DF.Data
    # end: auto-generated types

    @frappe.whitelist()
    def test_connection(self):
        """Test connection to BioTime server and return status"""
        try:
            from biotime.biotime.api.client import BioTimeClient

            client = BioTimeClient()
            token = client.get_auth_token()
            if token:
                self.db_set("connection_status", "Connected ✓")
                frappe.db.commit()
                return {
                    "success": True,
                    "message": "Connection successful! Token obtained.",
                }
            else:
                self.db_set("connection_status", "Failed - No token")
                frappe.db.commit()
                return {"success": False, "message": "Failed to obtain auth token."}
        except Exception as e:
            self.db_set("connection_status", f"Error: {str(e)[:100]}")
            frappe.db.commit()
            return {"success": False, "message": str(e)}

    @frappe.whitelist()
    def full_sync(self):
        """Trigger full sync of all data from BioTime"""
        from biotime.biotime.api.sync import full_sync

        frappe.enqueue(
            full_sync,
            queue="long",
            timeout=3600,
        )
        return {"message": "Full sync queued. Check Sync Log for progress."}

    @frappe.whitelist()
    def sync_transactions(self):
        """Trigger transaction sync from BioTime"""
        from biotime.biotime.api.sync import sync_transactions

        frappe.enqueue(
            sync_transactions,
            queue="long",
            timeout=1800,
        )
        return {"message": "Transaction sync queued. Check Sync Log for progress."}

    @frappe.whitelist()
    def sync_entity(self, entity):
        """Sync a specific entity type (devices, employees, departments, areas, positions)"""
        from biotime.biotime.api.sync import sync_entity

        frappe.enqueue(
            sync_entity,
            queue="default",
            timeout=600,
            entity=entity,
        )
        return {"message": f"{entity.title()} sync queued."}
