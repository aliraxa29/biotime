frappe.ui.form.on("BioTime Transaction Log", {
	refresh(frm) {
		if (!frm.is_new() && !frm.doc.checkin_created && frm.doc.erpnext_employee) {
			frm.add_custom_button(__("Create Employee Checkin"), function () {
				frm.call("create_employee_checkin").then((r) => {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __("Checkin {0} created", [r.message.checkin]),
							indicator: "green",
						});
						frm.reload_doc();
					} else {
						frappe.msgprint(r.message ? r.message.message : "Failed");
					}
				});
			});
		}

		// Show indicator for checkin status
		if (frm.doc.checkin_created) {
			frm.dashboard.set_headline(
				__("Employee Checkin: {0}", [
					`<a href="/app/employee-checkin/${frm.doc.employee_checkin}">${frm.doc.employee_checkin}</a>`,
				])
			);
		}
	},
});
