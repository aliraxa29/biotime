# Copyright (c) 2025, Ali Raxa and contributors
# For license information, please see license.txt

"""
BioTime Sync Module
Handles syncing data between BioTime 8.5 and ERPNext/HRMS.
Includes: devices, employees, departments, areas, positions, and transactions.
"""

from datetime import timedelta
import frappe
from frappe.utils import now_datetime, get_datetime, cstr


def full_sync():
	"""Run a full sync of all entities from BioTime"""
	sync_log = _create_sync_log("Full Sync")

	try:
		sync_log.status = "In Progress"
		sync_log.save(ignore_permissions=True)
		frappe.db.commit()

		total_created = 0
		total_updated = 0
		total_failed = 0
		details = []

		settings = frappe.get_single("BioTime Settings")

		# Sync in order of dependencies
		if settings.pull_departments:
			result = _sync_departments()
			total_created += result["created"]
			total_updated += result["updated"]
			total_failed += result["failed"]
			details.append(f"Departments: {result['created']} created, {result['updated']} updated, {result['failed']} failed")

		if settings.pull_areas:
			result = _sync_areas()
			total_created += result["created"]
			total_updated += result["updated"]
			total_failed += result["failed"]
			details.append(f"Areas: {result['created']} created, {result['updated']} updated, {result['failed']} failed")

		if settings.pull_positions:
			result = _sync_positions()
			total_created += result["created"]
			total_updated += result["updated"]
			total_failed += result["failed"]
			details.append(f"Positions: {result['created']} created, {result['updated']} updated, {result['failed']} failed")

		if settings.pull_devices:
			result = _sync_devices()
			total_created += result["created"]
			total_updated += result["updated"]
			total_failed += result["failed"]
			details.append(f"Devices: {result['created']} created, {result['updated']} updated, {result['failed']} failed")

		if settings.pull_employees:
			result = _sync_employees()
			total_created += result["created"]
			total_updated += result["updated"]
			total_failed += result["failed"]
			details.append(f"Employees: {result['created']} created, {result['updated']} updated, {result['failed']} failed")

		# Sync transactions
		tx_result = _sync_transaction_logs()
		details.append(
			f"Transactions: {tx_result['created']} new, {tx_result['checkins']} checkins created, {tx_result['failed']} failed"
		)

		sync_log.reload()
		sync_log.status = "Completed" if total_failed == 0 else "Partially Failed"
		sync_log.total_records = total_created + total_updated + total_failed
		sync_log.records_created = total_created + tx_result["created"]
		sync_log.records_updated = total_updated
		sync_log.records_failed = total_failed + tx_result["failed"]
		sync_log.checkins_created = tx_result["checkins"]
		sync_log.log_details = "\n".join(details)
		_complete_sync_log(sync_log)

		# Update last sync time
		frappe.db.set_single_value("BioTime Settings", "last_sync_time", now_datetime())
		frappe.db.commit()

	except Exception as e:
		_fail_sync_log(sync_log, str(e))
		frappe.log_error(title="BioTime Full Sync Failed", message=str(e))


def sync_transactions():
	"""Sync only transactions/punch logs from BioTime"""
	sync_log = _create_sync_log("Transactions")

	try:
		sync_log.status = "In Progress"
		sync_log.save(ignore_permissions=True)
		frappe.db.commit()

		result = _sync_transaction_logs()

		sync_log.reload()
		sync_log.status = "Completed" if result["failed"] == 0 else "Partially Failed"
		sync_log.total_records = result["total"]
		sync_log.records_created = result["created"]
		sync_log.records_failed = result["failed"]
		sync_log.checkins_created = result["checkins"]
		sync_log.log_details = (
			f"Total transactions fetched: {result['total']}\n"
			f"New transactions: {result['created']}\n"
			f"Skipped (already exists): {result['skipped']}\n"
			f"Employee Checkins created: {result['checkins']}\n"
			f"Failed: {result['failed']}"
		)
		_complete_sync_log(sync_log)

		# Update last transaction sync time
		frappe.db.set_single_value("BioTime Settings", "last_transaction_sync", now_datetime())
		frappe.db.commit()

	except Exception as e:
		_fail_sync_log(sync_log, str(e))
		frappe.log_error(title="BioTime Transaction Sync Failed", message=str(e))


@frappe.whitelist()
def sync_entity(entity):
	"""Sync a specific entity type"""
	entity_map = {
		"devices": ("Devices", _sync_devices),
		"employees": ("Employees", _sync_employees),
		"departments": ("Departments", _sync_departments),
		"areas": ("Areas", _sync_areas),
		"positions": ("Positions", _sync_positions),
	}

	if entity not in entity_map:
		frappe.throw(f"Unknown entity type: {entity}")

	label, sync_func = entity_map[entity]
	sync_log = _create_sync_log(label)

	try:
		sync_log.status = "In Progress"
		sync_log.save(ignore_permissions=True)
		frappe.db.commit()

		result = sync_func()

		sync_log.reload()
		sync_log.status = "Completed" if result["failed"] == 0 else "Partially Failed"
		sync_log.total_records = result["created"] + result["updated"] + result["failed"]
		sync_log.records_created = result["created"]
		sync_log.records_updated = result["updated"]
		sync_log.records_failed = result["failed"]
		_complete_sync_log(sync_log)

		return f"{label} synced: {result['created']} created, {result['updated']} updated, {result['failed']} failed"

	except Exception as e:
		_fail_sync_log(sync_log, str(e))
		frappe.throw(f"Sync failed: {str(e)}")


def _sync_devices():
	"""Sync devices from BioTime"""
	from biotime.biotime.api.client import BioTimeClient

	client = BioTimeClient()
	devices = client.get_devices()
	created, updated, failed = 0, 0, 0

	for device_data in devices:
		try:
			sn = device_data.get("sn")
			if not sn:
				continue

			# Get area info
			area_data = device_data.get("area")
			area_name = None
			if isinstance(area_data, dict):
				area_name = area_data.get("area_name")

			existing = frappe.db.exists("BioTime Device", sn)

			if existing:
				doc = frappe.get_doc("BioTime Device", sn)
			else:
				doc = frappe.new_doc("BioTime Device")
				doc.serial_number = sn

			doc.biotime_device_id = device_data.get("id")
			doc.alias = device_data.get("alias") or sn
			doc.terminal_name = device_data.get("terminal_name")
			doc.ip_address = device_data.get("ip_address")
			doc.status = "Online" if device_data.get("state") == 1 else "Offline"
			doc.firmware_version = device_data.get("fw_ver")
			doc.push_version = device_data.get("push_ver")
			doc.timezone = device_data.get("terminal_tz")
			doc.transfer_time = device_data.get("transfer_time")
			doc.transfer_interval = device_data.get("transfer_interval")
			doc.is_attendance = device_data.get("is_attendance", True)
			doc.user_count = device_data.get("user_count")
			doc.fp_count = device_data.get("fp_count")
			doc.face_count = device_data.get("face_count")
			doc.palm_count = device_data.get("palm_count")
			doc.transaction_count = device_data.get("transaction_count")

			if device_data.get("last_activity"):
				doc.last_activity = device_data["last_activity"]
			if device_data.get("push_time"):
				doc.push_time = device_data["push_time"]

			# Map area
			if area_name and frappe.db.exists("BioTime Area", area_name):
				doc.area = area_name

			doc.last_sync = now_datetime()
			doc.save(ignore_permissions=True)

			if existing:
				updated += 1
			else:
				created += 1

		except Exception as e:
			failed += 1
			frappe.log_error(
				title=f"BioTime Device Sync Error: {device_data.get('sn')}",
				message=str(e),
			)

	frappe.db.commit()
	return {"created": created, "updated": updated, "failed": failed}


def sync_single_device(device_id):
	"""Sync a single device from BioTime"""
	from biotime.biotime.api.client import BioTimeClient

	client = BioTimeClient()
	device_data = client.get_device(device_id)
	if not device_data:
		return

	sn = device_data.get("sn")
	if not sn:
		return

	existing = frappe.db.exists("BioTime Device", sn)
	if existing:
		doc = frappe.get_doc("BioTime Device", sn)
	else:
		doc = frappe.new_doc("BioTime Device")
		doc.serial_number = sn

	doc.biotime_device_id = device_data.get("id")
	doc.alias = device_data.get("alias") or sn
	doc.ip_address = device_data.get("ip_address")
	doc.status = "Online" if device_data.get("state") == 1 else "Offline"
	doc.firmware_version = device_data.get("fw_ver")
	doc.push_version = device_data.get("push_ver")
	doc.user_count = device_data.get("user_count")
	doc.fp_count = device_data.get("fp_count")
	doc.face_count = device_data.get("face_count")
	doc.palm_count = device_data.get("palm_count")
	doc.transaction_count = device_data.get("transaction_count")
	doc.last_sync = now_datetime()
	doc.save(ignore_permissions=True)
	frappe.db.commit()


def _sync_departments():
	"""Sync departments from BioTime"""
	from biotime.biotime.api.client import BioTimeClient

	client = BioTimeClient()
	departments = client.get_departments()
	created, updated, failed = 0, 0, 0

	# First pass: create/update all departments without parent
	dept_id_map = {}
	for dept_data in departments:
		try:
			dept_id = dept_data.get("id")
			dept_code = cstr(dept_data.get("dept_code"))
			dept_name = dept_data.get("dept_name")

			if not dept_code or not dept_name:
				continue

			dept_id_map[dept_id] = dept_name
			existing = frappe.db.exists("BioTime Department", dept_name)

			if existing:
				doc = frappe.get_doc("BioTime Department", dept_name)
			else:
				doc = frappe.new_doc("BioTime Department")
				doc.dept_name = dept_name

			doc.dept_code = dept_code
			doc.biotime_department_id = dept_id
			doc.last_sync = now_datetime()
			doc.save(ignore_permissions=True)

			if existing:
				updated += 1
			else:
				created += 1

		except Exception as e:
			failed += 1
			frappe.log_error(
				title=f"BioTime Dept Sync Error: {dept_data.get('dept_name')}",
				message=str(e),
			)

	# Second pass: set parent departments
	for dept_data in departments:
		try:
			dept_name = dept_data.get("dept_name")
			parent_dept = dept_data.get("parent_dept")

			if not dept_name or not parent_dept:
				continue

			parent_id = parent_dept
			if isinstance(parent_dept, dict):
				parent_id = parent_dept.get("id")

			parent_name = dept_id_map.get(parent_id)
			if parent_name and frappe.db.exists("BioTime Department", dept_name):
				frappe.db.set_value(
					"BioTime Department", dept_name, "parent_department", parent_name
				)
		except Exception:
			pass

	frappe.db.commit()
	return {"created": created, "updated": updated, "failed": failed}


def _sync_areas():
	"""Sync areas from BioTime"""
	from biotime.biotime.api.client import BioTimeClient

	client = BioTimeClient()
	areas = client.get_areas()
	created, updated, failed = 0, 0, 0

	area_id_map = {}
	for area_data in areas:
		try:
			area_id = area_data.get("id")
			area_code = cstr(area_data.get("area_code"))
			area_name = area_data.get("area_name")

			if not area_code or not area_name:
				continue

			area_id_map[area_id] = area_name
			existing = frappe.db.exists("BioTime Area", area_name)

			if existing:
				doc = frappe.get_doc("BioTime Area", area_name)
			else:
				doc = frappe.new_doc("BioTime Area")
				doc.area_name = area_name

			doc.area_code = area_code
			doc.biotime_area_id = area_id
			doc.last_sync = now_datetime()
			doc.save(ignore_permissions=True)

			if existing:
				updated += 1
			else:
				created += 1

		except Exception as e:
			failed += 1
			frappe.log_error(
				title=f"BioTime Area Sync Error: {area_data.get('area_name')}",
				message=str(e),
			)

	# Second pass: set parent areas
	for area_data in areas:
		try:
			area_name = area_data.get("area_name")
			parent_area = area_data.get("parent_area")

			if not area_name or not parent_area:
				continue

			parent_id = parent_area
			if isinstance(parent_area, dict):
				parent_id = parent_area.get("id")

			parent_name = area_id_map.get(parent_id)
			if parent_name and frappe.db.exists("BioTime Area", area_name):
				frappe.db.set_value(
					"BioTime Area", area_name, "parent_area", parent_name
				)
		except Exception:
			pass

	frappe.db.commit()
	return {"created": created, "updated": updated, "failed": failed}


def _sync_positions():
	"""Sync positions from BioTime"""
	from biotime.biotime.api.client import BioTimeClient

	client = BioTimeClient()
	positions = client.get_positions()
	created, updated, failed = 0, 0, 0

	pos_id_map = {}
	for pos_data in positions:
		try:
			pos_id = pos_data.get("id")
			pos_code = cstr(pos_data.get("position_code"))
			pos_name = pos_data.get("position_name")

			if not pos_code or not pos_name:
				continue

			pos_id_map[pos_id] = pos_name
			existing = frappe.db.exists("BioTime Position", pos_name)

			if existing:
				doc = frappe.get_doc("BioTime Position", pos_name)
			else:
				doc = frappe.new_doc("BioTime Position")
				doc.position_name = pos_name

			doc.position_code = pos_code
			doc.biotime_position_id = pos_id
			doc.last_sync = now_datetime()
			doc.save(ignore_permissions=True)

			if existing:
				updated += 1
			else:
				created += 1

		except Exception as e:
			failed += 1
			frappe.log_error(
				title=f"BioTime Position Sync Error: {pos_data.get('position_name')}",
				message=str(e),
			)

	# Second pass: set parent positions
	for pos_data in positions:
		try:
			pos_name = pos_data.get("position_name")
			parent_pos = pos_data.get("parent_position")

			if not pos_name or not parent_pos:
				continue

			parent_id = parent_pos
			if isinstance(parent_pos, dict):
				parent_id = parent_pos.get("id")

			parent_name = pos_id_map.get(parent_id)
			if parent_name and frappe.db.exists("BioTime Position", pos_name):
				frappe.db.set_value(
					"BioTime Position", pos_name, "parent_position", parent_name
				)
		except Exception:
			pass

	frappe.db.commit()
	return {"created": created, "updated": updated, "failed": failed}


def _sync_employees():
	"""Sync employees from BioTime"""
	from biotime.biotime.api.client import BioTimeClient

	client = BioTimeClient()
	employees = client.get_employees()
	settings = frappe.get_single("BioTime Settings")
	created, updated, failed = 0, 0, 0

	for emp_data in employees:
		try:
			emp_code = cstr(emp_data.get("emp_code"))
			if not emp_code:
				continue

			existing = frappe.db.exists("BioTime Employee", emp_code)

			if existing:
				doc = frappe.get_doc("BioTime Employee", emp_code)
			else:
				doc = frappe.new_doc("BioTime Employee")
				doc.emp_code = emp_code

			doc.biotime_employee_id = emp_data.get("id")
			doc.first_name = emp_data.get("first_name")
			doc.last_name = emp_data.get("last_name")
			doc.nickname = emp_data.get("nickname")
			doc.card_no = emp_data.get("card_no")
			doc.device_password = emp_data.get("device_password")
			doc.hire_date = emp_data.get("hire_date")
			doc.gender = emp_data.get("gender")
			doc.birthday = emp_data.get("birthday")
			doc.verify_mode = emp_data.get("verify_mode")
			doc.emp_type = cstr(emp_data.get("emp_type"))
			doc.dev_privilege = emp_data.get("dev_privilege")
			doc.enroll_sn = emp_data.get("enroll_sn")
			doc.enable_att = emp_data.get("enable_att", True)
			doc.enable_overtime = emp_data.get("enable_overtime", False)
			doc.enable_holiday = emp_data.get("enable_holiday", False)

			# Contact info
			doc.email = emp_data.get("email")
			doc.mobile = emp_data.get("mobile")
			doc.contact_tel = emp_data.get("contact_tel")
			doc.office_tel = emp_data.get("office_tel")
			doc.national = emp_data.get("national")
			doc.city = emp_data.get("city")
			doc.address = emp_data.get("address")
			doc.postcode = emp_data.get("postcode")
			doc.ssn = emp_data.get("ssn")
			doc.religion = emp_data.get("religion")
			doc.app_status = emp_data.get("app_status")
			doc.app_role = cstr(emp_data.get("app_role"))

			# Department mapping
			dept_data = emp_data.get("department")
			if isinstance(dept_data, dict):
				dept_name = dept_data.get("dept_name")
				if dept_name and frappe.db.exists("BioTime Department", dept_name):
					doc.department = dept_name
			elif dept_data:
				# dept_data is an ID, look up by biotime_department_id
				dept_name = frappe.db.get_value(
					"BioTime Department", {"biotime_department_id": dept_data}, "name"
				)
				if dept_name:
					doc.department = dept_name

			# Position mapping
			pos_data = emp_data.get("position")
			if isinstance(pos_data, dict):
				pos_name = pos_data.get("position_name")
				if pos_name and frappe.db.exists("BioTime Position", pos_name):
					doc.position = pos_name
			elif pos_data:
				pos_name = frappe.db.get_value(
					"BioTime Position", {"biotime_position_id": pos_data}, "name"
				)
				if pos_name:
					doc.position = pos_name

			# Area mapping
			area_data = emp_data.get("area")
			if isinstance(area_data, list) and area_data:
				first_area = area_data[0]
				if isinstance(first_area, dict):
					area_name = first_area.get("area_name")
					if area_name and frappe.db.exists("BioTime Area", area_name):
						doc.area = area_name
				elif first_area:
					area_name = frappe.db.get_value(
						"BioTime Area", {"biotime_area_id": first_area}, "name"
					)
					if area_name:
						doc.area = area_name

			# Auto-map to ERPNext employee if enabled
			if settings.auto_map_employees and not doc.erpnext_employee:
				_auto_map_employee(doc, settings)

			doc.last_sync = now_datetime()
			doc.save(ignore_permissions=True)

			if existing:
				updated += 1
			else:
				created += 1

		except Exception as e:
			failed += 1
			frappe.log_error(
				title=f"BioTime Employee Sync Error: {emp_data.get('emp_code')}",
				message=str(e),
			)

	frappe.db.commit()
	return {"created": created, "updated": updated, "failed": failed}


def _auto_map_employee(doc, settings):
	"""Try to automatically map a BioTime employee to an ERPNext Employee"""
	employee = None

	if settings.employee_id_field == "Attendance Device ID":
		employee = frappe.db.get_value(
			"Employee",
			{"attendance_device_id": doc.emp_code, "status": "Active"},
			"name",
		)
		# Also try card number
		if not employee and doc.card_no:
			employee = frappe.db.get_value(
				"Employee",
				{"attendance_device_id": doc.card_no, "status": "Active"},
				"name",
			)
	else:
		employee = frappe.db.get_value(
			"Employee",
			{"name": doc.emp_code, "status": "Active"},
			"name",
		)

	if employee:
		# Check no other BioTime employee is mapped to this
		existing_map = frappe.db.get_value(
			"BioTime Employee",
			{"erpnext_employee": employee, "name": ["!=", doc.name or ""]},
			"name",
		)
		if not existing_map:
			doc.erpnext_employee = employee
			doc.mapped = 1


def _sync_transaction_logs():
	"""Sync transaction logs (punch records) from BioTime and create Employee Checkins"""
	from biotime.biotime.api.client import BioTimeClient

	client = BioTimeClient()
	settings = frappe.get_single("BioTime Settings")

	# Determine time range
	if settings.last_transaction_sync:
		start_time = get_datetime(settings.last_transaction_sync).strftime(
			"%Y-%m-%d %H:%M:%S"
		)
	else:
		days_back = settings.sync_days_back or 7
		start_time = (now_datetime() - timedelta(days=days_back)).strftime(
			"%Y-%m-%d %H:%M:%S"
		)

	end_time = now_datetime().strftime("%Y-%m-%d %H:%M:%S")

	# Fetch transactions from BioTime
	transactions = client.get_transactions(start_time=start_time, end_time=end_time)

	total = len(transactions)
	created = 0
	skipped = 0
	failed = 0
	checkins = 0
	errors = []

	for txn in transactions:
		try:
			txn_id = txn.get("id")

			# Check if already imported
			if txn_id and frappe.db.exists(
				"BioTime Transaction Log", {"biotime_transaction_id": txn_id}
			):
				skipped += 1
				continue

			emp_code = cstr(txn.get("emp_code"))
			punch_time = txn.get("punch_time")

			if not emp_code or not punch_time:
				failed += 1
				continue

			# Also check for duplicate by emp_code + punch_time
			if frappe.db.exists(
				"BioTime Transaction Log",
				{"emp_code": emp_code, "punch_time": punch_time},
			):
				skipped += 1
				continue

			# Create transaction log
			log = frappe.new_doc("BioTime Transaction Log")
			log.biotime_transaction_id = txn_id
			log.emp_code = emp_code
			log.punch_time = punch_time
			log.punch_state = cstr(txn.get("punch_state"))
			log.device_sn = txn.get("terminal_sn")
			log.device_alias = txn.get("terminal_alias")
			log.area_alias = txn.get("area_alias")
			log.verify_type = txn.get("verify_type")
			log.work_code = txn.get("work_code")
			log.source = txn.get("source")
			log.purpose = txn.get("purpose")
			log.is_attendance = txn.get("is_attendance", 1)
			log.latitude = txn.get("latitude")
			log.longitude = txn.get("longitude")
			log.gps_location = txn.get("gps_location")
			log.mobile = txn.get("mobile")
			log.upload_time = txn.get("upload_time")
			log.sync_status = txn.get("sync_status")
			log.sync_time = txn.get("sync_time")

			# This triggers before_save which resolves employee and maps log_type
			log.insert(ignore_permissions=True)
			created += 1

			# Create Employee Checkin if enabled and employee is mapped
			if settings.create_employee_checkin and log.erpnext_employee:
				try:
					checkin_result = _create_employee_checkin(log)
					if checkin_result:
						checkins += 1
				except Exception as e:
					log.error_message = str(e)
					log.save(ignore_permissions=True)

		except Exception as e:
			failed += 1
			err_msg = f"Transaction {txn.get('id')}: {str(e)}"
			errors.append(err_msg)
			frappe.log_error(
				title=f"BioTime Transaction Sync Error: {txn.get('id')}",
				message=str(e),
			)

		# Commit in batches
		if (created + skipped + failed) % 100 == 0:
			frappe.db.commit()

	frappe.db.commit()

	return {
		"total": total,
		"created": created,
		"skipped": skipped,
		"failed": failed,
		"checkins": checkins,
		"errors": errors,
	}


def _create_employee_checkin(transaction_log):
	"""Create an Employee Checkin record from a BioTime Transaction Log"""
	if not transaction_log.erpnext_employee:
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
		transaction_log.checkin_created = 1
		transaction_log.employee_checkin = existing
		transaction_log.save(ignore_permissions=True)
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

	transaction_log.checkin_created = 1
	transaction_log.employee_checkin = checkin.name
	transaction_log.error_message = ""
	transaction_log.save(ignore_permissions=True)

	return True


def _create_sync_log(sync_type):
	"""Create a new BioTime Sync Log"""
	log = frappe.new_doc("BioTime Sync Log")
	log.sync_type = sync_type
	log.status = "Queued"
	log.started_at = now_datetime()
	log.triggered_by = frappe.session.user
	log.insert(ignore_permissions=True)
	frappe.db.commit()
	return log


def _complete_sync_log(sync_log):
	"""Mark sync log as completed"""
	sync_log.completed_at = now_datetime()
	if sync_log.started_at:
		delta = get_datetime(sync_log.completed_at) - get_datetime(sync_log.started_at)
		sync_log.duration_seconds = delta.total_seconds()
	sync_log.save(ignore_permissions=True)
	frappe.db.commit()


def _fail_sync_log(sync_log, error_message):
	"""Mark sync log as failed"""
	sync_log.reload()
	sync_log.status = "Failed"
	sync_log.completed_at = now_datetime()
	sync_log.error_log = error_message
	if sync_log.started_at:
		delta = get_datetime(sync_log.completed_at) - get_datetime(sync_log.started_at)
		sync_log.duration_seconds = delta.total_seconds()
	sync_log.save(ignore_permissions=True)
	frappe.db.commit()


def scheduled_sync():
	"""Called by scheduler to sync transactions if auto-sync is enabled"""
	settings = frappe.get_single("BioTime Settings")

	if not settings.enable_auto_sync:
		return

	# Check if enough time has passed since last sync
	interval = max(settings.sync_interval_minutes or 15, 5)  # Minimum 5 minutes

	if settings.last_transaction_sync:
		last_sync = get_datetime(settings.last_transaction_sync)
		next_sync = last_sync + timedelta(minutes=interval)
		if now_datetime() < next_sync:
			return

	# Run transaction sync
	sync_transactions()
