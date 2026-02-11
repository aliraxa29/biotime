# Copyright (c) 2025, Ali Raxa and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BioTimeTransactionLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		area_alias: DF.Data | None
		biotime_transaction_id: DF.Int
		checkin_created: DF.Check
		device_alias: DF.Data | None
		device_sn: DF.Data | None
		emp_code: DF.Data
		employee_checkin: DF.Link | None
		employee_name: DF.Data | None
		erpnext_employee: DF.Link | None
		error_message: DF.SmallText | None
		gps_location: DF.Data | None
		is_attendance: DF.Check
		latitude: DF.Float
		log_type: DF.Literal["", "IN", "OUT"]
		longitude: DF.Float
		mobile: DF.Data | None
		punch_state: DF.Data | None
		punch_time: DF.Datetime
		purpose: DF.Int
		source: DF.Int
		sync_status: DF.Int
		sync_time: DF.Datetime | None
		upload_time: DF.Datetime | None
		verify_type: DF.Int
		work_code: DF.Data | None
	# end: auto-generated types
	def before_save(self):
		"""Map punch_state to log_type and resolve employee"""
		self._map_log_type()
		self._resolve_employee()

	def _map_log_type(self):
		"""Map BioTime punch_state to IN/OUT log type"""
		if self.log_type:
			return

		punch_state_map = {
			"0": "IN",   # Check In
			"1": "OUT",  # Check Out
			"2": "OUT",  # Break Out
			"3": "IN",   # Break In
			"4": "IN",   # OT In
			"5": "OUT",  # OT Out
		}

		if self.punch_state and str(self.punch_state) in punch_state_map:
			self.log_type = punch_state_map[str(self.punch_state)]
		else:
			# Use default from settings
			settings = frappe.get_single("BioTime Settings")
			self.log_type = settings.default_log_type or ""

	def _resolve_employee(self):
		"""Try to find the ERPNext employee from emp_code"""
		if self.erpnext_employee:
			return

		# Look up BioTime Employee mapping
		biotime_emp = frappe.db.get_value(
			"BioTime Employee",
			{"emp_code": self.emp_code},
			["erpnext_employee", "first_name", "last_name"],
			as_dict=True,
		)

		if biotime_emp:
			if biotime_emp.erpnext_employee:
				self.erpnext_employee = biotime_emp.erpnext_employee
			name_parts = [biotime_emp.first_name or "", biotime_emp.last_name or ""]
			self.employee_name = " ".join(p for p in name_parts if p)

		if not self.erpnext_employee:
			# Try direct lookup by attendance_device_id
			employee = frappe.db.get_value(
				"Employee",
				{"attendance_device_id": self.emp_code, "status": "Active"},
				"name",
			)
			if employee:
				self.erpnext_employee = employee

	@frappe.whitelist()
	def create_employee_checkin(self):
		"""Manually create Employee Checkin for this transaction"""
		if self.checkin_created and self.employee_checkin:
			frappe.throw("Employee Checkin already created for this transaction")

		if not self.erpnext_employee:
			frappe.throw(
				"No ERPNext Employee mapped for this transaction. "
				"Please map the BioTime employee first."
			)

		try:
			checkin = frappe.new_doc("Employee Checkin")
			checkin.employee = self.erpnext_employee
			checkin.time = self.punch_time
			checkin.log_type = self.log_type or ""
			checkin.device_id = self.device_sn or ""
			if self.latitude:
				checkin.latitude = self.latitude
			if self.longitude:
				checkin.longitude = self.longitude
			checkin.insert(ignore_permissions=True)

			self.checkin_created = 1
			self.employee_checkin = checkin.name
			self.error_message = ""
			self.save(ignore_permissions=True)

			return {"success": True, "checkin": checkin.name}
		except Exception as e:
			self.error_message = str(e)
			self.save(ignore_permissions=True)
			return {"success": False, "message": str(e)}
