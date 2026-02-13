frappe.ui.form.on("BioTime Employee", {
	refresh(frm) {
		if (!frm.is_new()) {
			if (!frm.doc.erpnext_employee) {
				frm.add_custom_button(__("Auto Map to ERPNext"), function () {
					frm.call("auto_map_to_erpnext").then((r) => {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: __("Mapped to {0}", [r.message.employee]),
								indicator: "green",
							});
							frm.reload_doc();
						} else {
							frappe.msgprint(r.message ? r.message.message : "No match found");
						}
					});
				});
			} else {
				frm.add_custom_button(__("Validate Transaction Logs"), function () {
					frappe.call({
						method: "biotime.biotime.doctype.biotime_employee.biotime_employee.bulk_validate_transaction_logs",
						freeze: true,
						freeze_message: __("Validating transaction logs for {0}...", [frm.doc.emp_code]),
						callback: function (r) {
							if (r.message) {
								frappe.msgprint({
									title: __("Validation Complete"),
									message: __("Updated: {0} log(s), Checkins Created: {1}", [
										r.message.total_updated, r.message.total_checkins
									]),
									indicator: r.message.total_updated > 0 ? "green" : "blue",
								});
							}
						},
					});
				});
			}

			frm.add_custom_button(__("Push to BioTime"), function () {
				frm.call("push_to_biotime").then((r) => {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __("Employee pushed to BioTime"),
							indicator: "green",
						});
						frm.reload_doc();
					}
				});
			});
		}
	},
});
