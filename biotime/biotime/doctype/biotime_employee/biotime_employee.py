# Copyright (c) 2025, Ali Raxa and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BioTimeEmployee(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address: DF.SmallText | None
		app_role: DF.Data | None
		app_status: DF.Int
		area: DF.Link | None
		area_name: DF.Data | None
		biotime_employee_id: DF.Int
		birthday: DF.Date | None
		card_no: DF.Data | None
		city: DF.Data | None
		contact_tel: DF.Data | None
		department: DF.Link | None
		department_name: DF.Data | None
		dev_privilege: DF.Int
		device_password: DF.Data | None
		email: DF.Data | None
		emp_code: DF.Data
		emp_type: DF.Data | None
		enable_att: DF.Check
		enable_holiday: DF.Check
		enable_overtime: DF.Check
		enroll_sn: DF.Data | None
		erpnext_employee: DF.Link | None
		erpnext_employee_name: DF.Data | None
		first_name: DF.Data | None
		gender: DF.Data | None
		hire_date: DF.Date | None
		last_name: DF.Data | None
		last_sync: DF.Datetime | None
		mapped: DF.Check
		mobile: DF.Data | None
		national: DF.Data | None
		nickname: DF.Data | None
		office_tel: DF.Data | None
		position: DF.Link | None
		position_name: DF.Data | None
		postcode: DF.Data | None
		religion: DF.Data | None
		ssn: DF.Data | None
		verify_mode: DF.Int
	# end: auto-generated types
	def before_save(self):
		"""Update mapped status based on ERPNext Employee link"""
		self.mapped = 1 if self.erpnext_employee else 0
		self._prev_erpnext_employee = (
			self.get_doc_before_save() or frappe._dict()
		).get("erpnext_employee")

	def on_update(self):
		"""After saving, if erpnext_employee was newly set, validate pending transaction logs"""
		prev = getattr(self, "_prev_erpnext_employee", None)
		if self.erpnext_employee and self.erpnext_employee != prev:
			# Employee was just mapped — backfill transaction logs
			updated, checkins = backfill_transaction_logs_for_employee(
				self.emp_code, self.erpnext_employee
			)
			if updated:
				frappe.msgprint(
					f"Updated {updated} transaction log(s) with ERPNext Employee "
					f"and created {checkins} Employee Checkin(s).",
					alert=True,
				)

	def validate(self):
		"""Validate the employee record"""
		if self.erpnext_employee:
			# Ensure no other BioTime Employee is mapped to same ERPNext employee
			existing = frappe.db.get_value(
				"BioTime Employee",
				{"erpnext_employee": self.erpnext_employee, "name": ["!=", self.name]},
				"name",
			)
			if existing:
				frappe.throw(
					f"ERPNext Employee {self.erpnext_employee} is already mapped to BioTime Employee {existing}"
				)

	@frappe.whitelist()
	def auto_map_to_erpnext(self):
		"""Try to automatically map this BioTime employee to an ERPNext employee"""
		settings = frappe.get_single("BioTime Settings")

		employee = None
		if settings.employee_id_field == "Attendance Device ID":
			employee = frappe.db.get_value(
				"Employee",
				{"attendance_device_id": self.emp_code, "status": "Active"},
				"name",
			)
		else:
			employee = frappe.db.get_value(
				"Employee",
				{"name": self.emp_code, "status": "Active"},
				"name",
			)

		if not employee and self.card_no:
			employee = frappe.db.get_value(
				"Employee",
				{"attendance_device_id": self.card_no, "status": "Active"},
				"name",
			)

		if employee:
			self.erpnext_employee = employee
			self.mapped = 1
			self.save()
			return {"success": True, "employee": employee}
		else:
			return {
				"success": False,
				"message": f"No matching ERPNext Employee found for emp_code: {self.emp_code}",
			}

	@frappe.whitelist()
	def push_to_biotime(self):
		"""Push this employee record to BioTime"""
		from biotime.biotime.api.client import BioTimeClient

		client = BioTimeClient()

		data = {
			"emp_code": self.emp_code,
			"first_name": self.first_name or "",
			"last_name": self.last_name or "",
		}

		if self.department:
			dept_id = frappe.db.get_value(
				"BioTime Department", self.department, "biotime_department_id"
			)
			if dept_id:
				data["department"] = dept_id

		if self.biotime_employee_id:
			# Update
			result = client.update_employee(self.biotime_employee_id, data)
		else:
			# Create
			result = client.create_employee(data)
			if result and result.get("id"):
				self.biotime_employee_id = result["id"]
				self.save()

		return {"success": True, "result": result}


def backfill_transaction_logs_for_employee(emp_code, erpnext_employee):
	"""
	Backfill ERPNext Employee on transaction logs for the given emp_code.
	Also creates missing Employee Checkins.

	This handles the case where transaction logs were synced before the
	BioTime Employee was mapped to an ERPNext Employee.

	Returns:
		tuple: (updated_count, checkins_created)
	"""
	# Find all transaction logs for this emp_code that are missing erpnext_employee
	logs = frappe.get_all(
		"BioTime Transaction Log",
		filters={
			"emp_code": emp_code,
			"erpnext_employee": ["is", "not set"],
		},
		fields=["name"],
		order_by="punch_time asc",
	)

	if not logs:
		return 0, 0

	settings = frappe.get_single("BioTime Settings")
	updated = 0
	checkins_created = 0

	for log_ref in logs:
		try:
			log = frappe.get_doc("BioTime Transaction Log", log_ref.name)
			log.erpnext_employee = erpnext_employee
			log.save(ignore_permissions=True)
			updated += 1

			# Create Employee Checkin if enabled and not already created
			if settings.create_employee_checkin and not log.checkin_created:
				try:
					_create_checkin_for_log(log)
					checkins_created += 1
				except Exception as e:
					log.db_set("error_message", str(e), update_modified=False)
		except Exception as e:
			frappe.log_error(
				title=f"Backfill Transaction Log Error: {log_ref.name}",
				message=str(e),
			)

	frappe.db.commit()
	return updated, checkins_created


def _create_checkin_for_log(transaction_log):
	"""Create an Employee Checkin from a transaction log if not already exists."""
	if not transaction_log.erpnext_employee or transaction_log.checkin_created:
		return False

	# Check for duplicate checkin
	existing = frappe.db.exists(
		"Employee Checkin",
		{
			"employee": transaction_log.erpnext_employee,
			"time": transaction_log.punch_time,
		},
	)
	if existing:
		transaction_log.db_set("checkin_created", 1, update_modified=False)
		transaction_log.db_set("employee_checkin", existing, update_modified=False)
		return False

	checkin = frappe.new_doc("Employee Checkin")
	checkin.employee = transaction_log.erpnext_employee
	checkin.time = transaction_log.punch_time
	checkin.log_type = transaction_log.log_type or ""
	checkin.device_id = transaction_log.device_sn or ""

	if transaction_log.latitude:
		checkin.latitude = transaction_log.latitude
	if transaction_log.longitude:
		checkin.longitude = transaction_log.longitude

	checkin.insert(ignore_permissions=True)

	transaction_log.db_set("checkin_created", 1, update_modified=False)
	transaction_log.db_set("employee_checkin", checkin.name, update_modified=False)
	transaction_log.db_set("error_message", "", update_modified=False)
	return True


@frappe.whitelist()
def bulk_validate_transaction_logs():
	"""
	Bulk validate all BioTime Transaction Logs that are missing an ERPNext Employee.
	Looks up the BioTime Employee mapping and backfills erpnext_employee + creates
	missing Employee Checkins.

	This is useful when:
	- Transaction logs were synced before employees were fetched from the machine
	- Employee mappings were done after the sync
	- Some logs missed the employee resolution during initial sync

	Can be triggered from BioTime Settings or called via API.
	"""
	# Get all unmapped transaction logs
	unmapped_logs = frappe.db.sql(
		"""
		SELECT DISTINCT tl.emp_code
		FROM `tabBioTime Transaction Log` tl
		WHERE tl.erpnext_employee IS NULL OR tl.erpnext_employee = ''
		""",
		as_dict=True,
	)

	if not unmapped_logs:
		return {"message": "No unmapped transaction logs found.", "total_updated": 0, "total_checkins": 0}

	total_updated = 0
	total_checkins = 0
	emp_codes_fixed = []
	emp_codes_skipped = []

	for row in unmapped_logs:
		emp_code = row.emp_code

		# Look up BioTime Employee to get the ERPNext Employee mapping
		erpnext_employee = frappe.db.get_value(
			"BioTime Employee",
			{"emp_code": emp_code, "erpnext_employee": ["is", "set"]},
			"erpnext_employee",
		)

		if not erpnext_employee:
			# Try direct lookup by attendance_device_id
			erpnext_employee = frappe.db.get_value(
				"Employee",
				{"attendance_device_id": emp_code, "status": "Active"},
				"name",
			)

		if erpnext_employee:
			updated, checkins = backfill_transaction_logs_for_employee(emp_code, erpnext_employee)
			total_updated += updated
			total_checkins += checkins
			emp_codes_fixed.append(emp_code)
		else:
			emp_codes_skipped.append(emp_code)

	result = {
		"message": (
			f"Bulk validation complete. "
			f"Updated {total_updated} transaction log(s), "
			f"created {total_checkins} Employee Checkin(s). "
			f"Fixed employee codes: {len(emp_codes_fixed)}. "
			f"Skipped (no mapping found): {len(emp_codes_skipped)}."
		),
		"total_updated": total_updated,
		"total_checkins": total_checkins,
		"fixed_emp_codes": emp_codes_fixed,
		"skipped_emp_codes": emp_codes_skipped,
	}

	frappe.msgprint(result["message"])
	return result