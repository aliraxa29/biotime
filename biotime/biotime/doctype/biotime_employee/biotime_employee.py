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
