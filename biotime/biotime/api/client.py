# Copyright (c) 2025, Ali Raxa and contributors
# For license information, please see license.txt

"""
BioTime 8.5 API Client
Handles authentication, token management, and all API calls to BioTime server.
Based on BioTime 8.5 API User Manual.
"""

import requests
import frappe


class BioTimeClient:
	"""HTTP client for BioTime 8.5 REST API"""

	def __init__(self):
		self.settings = frappe.get_single("BioTime Settings")
		self.base_url = self.settings.server_url.rstrip("/")
		self.username = self.settings.username
		self.password = self.settings.get_password("password")
		self.token_type = self.settings.auth_token_type or "JWT"
		self._token = None
		self._session = requests.Session()
		self._session.headers.update({"Content-Type": "application/json"})

	def _get_url(self, path):
		"""Build full URL from path"""
		if not path.startswith("/"):
			path = "/" + path
		return self.base_url + path

	def get_auth_token(self, force_refresh=False):
		"""Get authentication token. Fetches a new one if not cached or force_refresh is True."""
		if not force_refresh and self._token:
			return self._token

		# Check if we have a cached token in settings
		if not force_refresh and self.settings.auth_token:
			try:
				token = self.settings.get_password("auth_token")
			except Exception:
				token = None
			if token:
				self._token = token
				return self._token

		# Request new token from BioTime
		if self.token_type == "JWT":
			token = self._get_jwt_token()
		else:
			token = self._get_general_token()

		if token:
			self._token = token
			# Cache token in settings
			frappe.db.set_single_value("BioTime Settings", "auth_token", token)
			frappe.db.commit()

		return self._token

	def _get_jwt_token(self):
		"""Get JWT auth token from BioTime"""
		url = self._get_url("/jwt-api-token-auth/")
		payload = {"username": self.username, "password": self.password}

		try:
			response = self._session.post(url, json=payload, timeout=30)
			response.raise_for_status()
			data = response.json()
			return data.get("token")
		except requests.exceptions.RequestException as e:
			frappe.log_error(
				title="BioTime JWT Auth Failed",
				message=f"URL: {url}\nError: {str(e)}",
			)
			raise Exception(f"BioTime JWT authentication failed: {str(e)}")

	def _get_general_token(self):
		"""Get general auth token from BioTime"""
		url = self._get_url("/api-token-auth/")
		payload = {"username": self.username, "password": self.password}

		try:
			response = self._session.post(url, json=payload, timeout=30)
			response.raise_for_status()
			data = response.json()
			return data.get("token")
		except requests.exceptions.RequestException as e:
			frappe.log_error(
				title="BioTime General Auth Failed",
				message=f"URL: {url}\nError: {str(e)}",
			)
			raise Exception(f"BioTime general authentication failed: {str(e)}")

	def _get_auth_header(self):
		"""Get Authorization header with token"""
		token = self.get_auth_token()
		if not token:
			raise Exception("No auth token available. Please test connection first.")

		if self.token_type == "JWT":
			return {"Authorization": f"JWT {token}"}
		else:
			return {"Authorization": f"Token {token}"}


	def _request(self, method, path, params=None, data=None, retry=True):
		"""Make an authenticated request to BioTime API"""
		url = self._get_url(path)
		headers = self._get_auth_header()

		try:
			response = self._session.request(
				method=method,
				url=url,
				headers=headers,
				params=params,
				json=data,
				timeout=60,
			)
			if response.status_code == 401 and retry:
				self.get_auth_token(force_refresh=True)
				return self._request(method, path, params, data, retry=False)

			response.raise_for_status()
			return response.json()

		except requests.exceptions.RequestException as e:
			frappe.log_error(
				title=f"BioTime API Error ({method} {path})",
				message=f"URL: {url}\nParams: {params}\nData: {data}\nError: {str(e)}",
			)
			raise

	def _get(self, path, params=None):
		return self._request("GET", path, params=params)

	def _post(self, path, data=None):
		return self._request("POST", path, data=data)

	def _patch(self, path, data=None):
		return self._request("PATCH", path, data=data)

	def _delete(self, path):
		return self._request("DELETE", path)

	def _get_all_pages(self, path, params=None):
		"""Fetch all pages of a paginated API endpoint"""
		if params is None:
			params = {}

		all_results = []
		page = 1
		page_size = 100
		params["page_size"] = page_size

		while True:
			params["page"] = page
			response = self._get(path, params)

			results = response.get("data", response.get("results", []))
			if not results:
				break

			all_results.extend(results)

			# Check if there are more pages
			if response.get("next") is None:
				break

			total = response.get("count", 0)
			if len(all_results) >= total:
				break

			page += 1

		return all_results


	def get_devices(self, **filters):
		"""Get list of all devices
		Filters: sn, alias, area, page, page_size
		"""
		return self._get_all_pages("/iclock/api/terminals/", params=filters)

	def get_device(self, device_id):
		"""Get single device by ID"""
		return self._get(f"/iclock/api/terminals/{device_id}/")

	def get_employees(self, **filters):
		"""Get list of all employees
		Filters: emp_code, first_name, last_name, department, app_status, page, page_size
		"""
		return self._get_all_pages("/personnel/api/employees/", params=filters)

	def get_employee(self, employee_id):
		"""Get single employee by ID"""
		return self._get(f"/personnel/api/employees/{employee_id}/")

	def create_employee(self, data):
		"""Create a new employee in BioTime
		Required: emp_code, first_name
		Optional: last_name, department, area, position, hire_date, etc.
		"""
		return self._post("/personnel/api/employees/", data=data)

	def update_employee(self, employee_id, data):
		"""Update an existing employee in BioTime"""
		return self._patch(f"/personnel/api/employees/{employee_id}/", data=data)

	def delete_employee(self, employee_id):
		"""Delete an employee from BioTime"""
		return self._delete(f"/personnel/api/employees/{employee_id}/")

	def get_departments(self, **filters):
		"""Get list of all departments
		Filters: dept_code, dept_name, parent_dept, page, page_size
		"""
		return self._get_all_pages("/personnel/api/departments/", params=filters)

	def get_department(self, dept_id):
		"""Get single department by ID"""
		return self._get(f"/personnel/api/departments/{dept_id}/")

	def create_department(self, data):
		"""Create a new department in BioTime
		Required: dept_code, dept_name
		Optional: parent_dept
		"""
		return self._post("/personnel/api/departments/", data=data)

	def update_department(self, dept_id, data):
		"""Update a department in BioTime"""
		return self._patch(f"/personnel/api/departments/{dept_id}/", data=data)

	def delete_department(self, dept_id):
		"""Delete a department from BioTime"""
		return self._delete(f"/personnel/api/departments/{dept_id}/")

	def get_areas(self, **filters):
		"""Get list of all areas
		Filters: area_code, area_name, parent_area, page, page_size
		"""
		return self._get_all_pages("/personnel/api/areas/", params=filters)

	def get_area(self, area_id):
		"""Get single area by ID"""
		return self._get(f"/personnel/api/areas/{area_id}/")

	def create_area(self, data):
		"""Create a new area in BioTime
		Required: area_code, area_name
		Optional: parent_area
		"""
		return self._post("/personnel/api/areas/", data=data)

	def update_area(self, area_id, data):
		"""Update an area in BioTime"""
		return self._patch(f"/personnel/api/areas/{area_id}/", data=data)

	def delete_area(self, area_id):
		"""Delete an area from BioTime"""
		return self._delete(f"/personnel/api/areas/{area_id}/")

	def get_positions(self, **filters):
		"""Get list of all positions
		Filters: position_code, position_name, parent_position, page, page_size
		"""
		return self._get_all_pages("/personnel/api/positions/", params=filters)

	def get_position(self, position_id):
		"""Get single position by ID"""
		return self._get(f"/personnel/api/positions/{position_id}/")

	def create_position(self, data):
		"""Create a new position in BioTime
		Required: position_code, position_name
		Optional: parent_position
		"""
		return self._post("/personnel/api/positions/", data=data)

	def update_position(self, position_id, data):
		"""Update a position in BioTime"""
		return self._patch(f"/personnel/api/positions/{position_id}/", data=data)

	def delete_position(self, position_id):
		"""Delete a position from BioTime"""
		return self._delete(f"/personnel/api/positions/{position_id}/")

	def get_transactions(self, **filters):
		"""Get list of transactions (punch logs)
		Filters: emp_code, terminal_sn, start_time, end_time, page, page_size
		"""
		return self._get_all_pages("/iclock/api/transactions/", params=filters)

	def get_transactions_page(self, page=1, page_size=100, **filters):
		"""Get a single page of transactions"""
		params = {"page": page, "page_size": page_size}
		params.update(filters)
		return self._get("/iclock/api/transactions/", params=params)
