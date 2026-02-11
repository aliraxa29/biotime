# Copyright (c) 2025, Ali Raxa and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BioTimeSyncLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		checkins_created: DF.Int
		completed_at: DF.Datetime | None
		duration_seconds: DF.Float
		error_log: DF.LongText | None
		log_details: DF.LongText | None
		records_created: DF.Int
		records_failed: DF.Int
		records_updated: DF.Int
		started_at: DF.Datetime | None
		status: DF.Literal["Queued", "In Progress", "Completed", "Failed", "Partially Failed"]
		sync_type: DF.Literal["Full Sync", "Transactions", "Devices", "Employees", "Departments", "Areas", "Positions"]
		total_records: DF.Int
		triggered_by: DF.Link | None
	# end: auto-generated types
	pass
