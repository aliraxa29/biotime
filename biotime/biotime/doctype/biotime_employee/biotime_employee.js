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
