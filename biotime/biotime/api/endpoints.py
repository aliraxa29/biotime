# Copyright (c) 2025, Ali Raxa and contributors
# For license information, please see license.txt

"""
Whitelisted API endpoints for BioTime integration.
These can be called from the frontend or external systems.
"""

import frappe

@frappe.whitelist()
def add_device_to_biotime(serial_number, alias=None, ip_address=None, area_id=None):
	"""Register a new device in BioTime via API
	Note: BioTime typically auto-discovers devices. This is for manual registration.
	"""
	settings = frappe.get_single("BioTime Settings")
	if settings.block_new_registrations:
		frappe.throw("New device registrations are blocked. Disable this in BioTime Settings.")

	from biotime.biotime.api.client import BioTimeClient

	client = BioTimeClient()

	# First check if device exists in BioTime
	devices = client.get_devices(sn=serial_number)
	if devices:
		frappe.throw(f"Device with SN {serial_number} already exists in BioTime")

	frappe.msgprint(
		f"Device {serial_number} needs to be added directly in BioTime "
		"(devices register themselves via push protocol). "
		"Use 'Sync Devices' to pull it into ERPNext after it appears in BioTime."
	)


@frappe.whitelist()
def test_device(serial_number):
	"""Test a specific device connection via BioTime"""
	from biotime.biotime.api.client import BioTimeClient

	client = BioTimeClient()

	# Find device by SN
	devices = client.get_devices(sn=serial_number)
	if not devices:
		return {"success": False, "message": f"Device {serial_number} not found in BioTime"}

	device = devices[0]
	state = device.get("state", 0)
	status = "Online" if state == 1 else "Offline"

	# Update local record
	if frappe.db.exists("BioTime Device", serial_number):
		frappe.db.set_value("BioTime Device", serial_number, "status", status)
		frappe.db.commit()

	return {
		"success": True,
		"status": status,
		"device": {
			"sn": device.get("sn"),
			"alias": device.get("alias"),
			"ip": device.get("ip_address"),
			"fw": device.get("fw_ver"),
			"users": device.get("user_count"),
			"last_activity": device.get("last_activity"),
		},
	}


@frappe.whitelist()
def push_employee_to_biotime(emp_code, first_name, last_name=None, department_id=None, area_ids=None):
	"""Create or update an employee in BioTime"""
	from biotime.biotime.api.client import BioTimeClient

	client = BioTimeClient()

	data = {
		"emp_code": emp_code,
		"first_name": first_name,
	}
	if last_name:
		data["last_name"] = last_name
	if department_id:
		data["department"] = int(department_id)
	if area_ids:
		if isinstance(area_ids, str):
			area_ids = frappe.parse_json(area_ids)
		data["area"] = area_ids

	# Check if employee already exists by looking up biotime_employee_id
	biotime_id = frappe.db.get_value("BioTime Employee", emp_code, "biotime_employee_id")

	if biotime_id:
		result = client.update_employee(biotime_id, data)
		return {"success": True, "action": "updated", "result": result}
	else:
		result = client.create_employee(data)
		if result and result.get("id"):
			frappe.db.set_value("BioTime Employee", emp_code, "biotime_employee_id", result["id"])
			frappe.db.commit()
		return {"success": True, "action": "created", "result": result}


@frappe.whitelist()
def delete_employee_from_biotime(emp_code):
	"""Delete an employee from BioTime"""
	from biotime.biotime.api.client import BioTimeClient

	biotime_id = frappe.db.get_value("BioTime Employee", emp_code, "biotime_employee_id")
	if not biotime_id:
		frappe.throw(f"BioTime Employee ID not found for {emp_code}")

	client = BioTimeClient()
	client.delete_employee(biotime_id)
	return {"success": True, "message": f"Employee {emp_code} deleted from BioTime"}


@frappe.whitelist()
def auto_map_all_employees():
	"""
	Try to auto-map all unmapped BioTime employees to ERPNext employees.
	Uses the configured matching field (Attendance Device ID or Employee ID).
	"""
	settings = frappe.get_single("BioTime Settings")
	unmapped = frappe.get_all(
		"BioTime Employee",
		filters={"mapped": 0},
		fields=["name", "emp_code", "card_no"],
	)

	mapped_count = 0
	for emp in unmapped:
		employee = None

		if settings.employee_id_field == "Attendance Device ID":
			employee = frappe.db.get_value(
				"Employee",
				{"attendance_device_id": emp.emp_code, "status": "Active"},
				"name",
			)
			if not employee and emp.card_no:
				employee = frappe.db.get_value(
					"Employee",
					{"attendance_device_id": emp.card_no, "status": "Active"},
					"name",
				)
		else:
			employee = frappe.db.get_value(
				"Employee", {"name": emp.emp_code, "status": "Active"}, "name"
			)

		if employee:
			# Ensure not already mapped
			existing = frappe.db.get_value(
				"BioTime Employee",
				{"erpnext_employee": employee, "name": ["!=", emp.name]},
				"name",
			)
			if not existing:
				frappe.db.set_value("BioTime Employee", emp.name, {
					"erpnext_employee": employee,
					"mapped": 1,
				})
				mapped_count += 1

	frappe.db.commit()
	return {
		"total_unmapped": len(unmapped),
		"newly_mapped": mapped_count,
		"still_unmapped": len(unmapped) - mapped_count,
	}


@frappe.whitelist()
def create_missing_checkins():
	"""Create Employee Checkin records for all transaction logs that are mapped but don't have checkins yet"""
	logs = frappe.get_all(
		"BioTime Transaction Log",
		filters={
			"checkin_created": 0,
			"erpnext_employee": ["is", "set"],
		},
		fields=["name"],
		limit=500,
	)

	created = 0
	failed = 0

	for log_data in logs:
		try:
			log = frappe.get_doc("BioTime Transaction Log", log_data.name)
			result = log.create_employee_checkin()
			if result and result.get("success"):
				created += 1
			else:
				failed += 1
		except Exception:
			failed += 1

	frappe.db.commit()
	return {"created": created, "failed": failed, "total": len(logs)}


@frappe.whitelist()
def push_department_to_biotime(dept_code, dept_name, parent_dept_id=None):
	"""Create or update a department in BioTime"""
	from biotime.biotime.api.client import BioTimeClient

	client = BioTimeClient()
	data = {"dept_code": dept_code, "dept_name": dept_name}
	if parent_dept_id:
		data["parent_dept"] = int(parent_dept_id)

	biotime_id = frappe.db.get_value(
		"BioTime Department", dept_name, "biotime_department_id"
	)

	if biotime_id:
		result = client.update_department(biotime_id, data)
		return {"success": True, "action": "updated", "result": result}
	else:
		result = client.create_department(data)
		if result and result.get("id"):
			frappe.db.set_value(
				"BioTime Department", dept_name, "biotime_department_id", result["id"]
			)
			frappe.db.commit()
		return {"success": True, "action": "created", "result": result}


@frappe.whitelist()
def delete_department_from_biotime(dept_name):
	"""Delete a department from BioTime"""
	from biotime.biotime.api.client import BioTimeClient

	biotime_id = frappe.db.get_value(
		"BioTime Department", dept_name, "biotime_department_id"
	)
	if not biotime_id:
		frappe.throw(f"BioTime Department ID not found for {dept_name}")

	client = BioTimeClient()
	client.delete_department(biotime_id)
	return {"success": True, "message": f"Department {dept_name} deleted from BioTime"}


@frappe.whitelist()
def push_area_to_biotime(area_code, area_name, parent_area_id=None):
	"""Create or update an area in BioTime"""
	from biotime.biotime.api.client import BioTimeClient

	client = BioTimeClient()
	data = {"area_code": area_code, "area_name": area_name}
	if parent_area_id:
		data["parent_area"] = int(parent_area_id)

	biotime_id = frappe.db.get_value("BioTime Area", area_name, "biotime_area_id")

	if biotime_id:
		result = client.update_area(biotime_id, data)
		return {"success": True, "action": "updated", "result": result}
	else:
		result = client.create_area(data)
		if result and result.get("id"):
			frappe.db.set_value("BioTime Area", area_name, "biotime_area_id", result["id"])
			frappe.db.commit()
		return {"success": True, "action": "created", "result": result}


@frappe.whitelist()
def push_position_to_biotime(position_code, position_name, parent_position_id=None):
	"""Create or update a position in BioTime"""
	from biotime.biotime.api.client import BioTimeClient

	client = BioTimeClient()
	data = {"position_code": position_code, "position_name": position_name}
	if parent_position_id:
		data["parent_position"] = int(parent_position_id)

	biotime_id = frappe.db.get_value(
		"BioTime Position", position_name, "biotime_position_id"
	)

	if biotime_id:
		result = client.update_position(biotime_id, data)
		return {"success": True, "action": "updated", "result": result}
	else:
		result = client.create_position(data)
		if result and result.get("id"):
			frappe.db.set_value(
				"BioTime Position", position_name, "biotime_position_id", result["id"]
			)
			frappe.db.commit()
		return {"success": True, "action": "created", "result": result}


@frappe.whitelist()
def get_biotime_dashboard_data():
	"""Get summary data for BioTime dashboard"""
	data = {
		"devices": {
			"total": frappe.db.count("BioTime Device"),
			"online": frappe.db.count("BioTime Device", {"status": "Online"}),
			"offline": frappe.db.count("BioTime Device", {"status": "Offline"}),
		},
		"employees": {
			"total": frappe.db.count("BioTime Employee"),
			"mapped": frappe.db.count("BioTime Employee", {"mapped": 1}),
			"unmapped": frappe.db.count("BioTime Employee", {"mapped": 0}),
		},
		"transactions": {
			"total": frappe.db.count("BioTime Transaction Log"),
			"with_checkin": frappe.db.count("BioTime Transaction Log", {"checkin_created": 1}),
			"without_checkin": frappe.db.count("BioTime Transaction Log", {"checkin_created": 0}),
		},
		"departments": frappe.db.count("BioTime Department"),
		"areas": frappe.db.count("BioTime Area"),
		"positions": frappe.db.count("BioTime Position"),
	}

	# Last sync info
	settings = frappe.get_single("BioTime Settings")
	data["last_sync"] = settings.last_sync_time
	data["last_transaction_sync"] = settings.last_transaction_sync
	data["auto_sync_enabled"] = settings.enable_auto_sync

	# Recent sync logs
	data["recent_syncs"] = frappe.get_all(
		"BioTime Sync Log",
		fields=["name", "sync_type", "status", "started_at", "total_records", "checkins_created"],
		order_by="creation desc",
		limit=5,
	)

	return data
