# Copyright (c) 2025, Ali Raxa and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BioTimeDevice(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		alias: DF.Data | None
		amended_from: DF.Link | None
		area: DF.Link | None
		area_name: DF.Data | None
		biotime_device_id: DF.Int
		face_count: DF.Int
		firmware_version: DF.Data | None
		fp_count: DF.Int
		ip_address: DF.Data | None
		is_attendance: DF.Check
		last_activity: DF.Datetime | None
		last_sync: DF.Datetime | None
		palm_count: DF.Int
		push_time: DF.Datetime | None
		push_version: DF.Data | None
		serial_number: DF.Data
		status: DF.Literal["Online", "Offline", "Unknown"]
		terminal_name: DF.Data | None
		timezone: DF.Int
		transaction_count: DF.Int
		transfer_interval: DF.Int
		transfer_time: DF.Data | None
		user_count: DF.Int
	# end: auto-generated types
	def before_save(self):
		if not self.alias:
			self.alias = self.serial_number

	@frappe.whitelist()
	def ping_device(self):
		"""Test connection to this specific device via BioTime"""
		from biotime.biotime.api.client import BioTimeClient

		client = BioTimeClient()
		device_info = client.get_device(self.biotime_device_id)
		if device_info:
			state = device_info.get("state", 0)
			self.status = "Online" if state == 1 else "Offline"
			self.save()
			return {"success": True, "status": self.status}
		return {"success": False, "message": "Device not found in BioTime"}

	@frappe.whitelist()
	def sync_from_biotime(self):
		"""Refresh device data from BioTime"""
		from biotime.biotime.api.sync import sync_single_device

		sync_single_device(self.biotime_device_id)
		self.reload()
		return {"success": True, "message": "Device synced successfully"}
