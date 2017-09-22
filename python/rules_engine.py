#This file will contain the python class used to check LAR data using the edits as described in the HMDA FIG
#This class should be able to return a list of row fail counts for each S/V edit for each file passed to the class.
#The return should be JSON formatted data, written to a file?
#input to the class will be a pandas dataframe
from collections import OrderedDict
from io import StringIO
import pandas as pd
import time

from lar_generator import lar_gen #used for check digit

class rules_engine(object):
	"""docstring for ClassName"""
	def __init__(self, lar_schema=None, ts_schema=None, path="../edits_files/", data_file="passes_all.txt", year="2018", tracts=None, counties=None):
		#lar and TS field names (load from schema names?)
		self.year = year
		self.tracts = tracts #instantiate valid Census tracts
		self.counties = counties #instantiate valid Census counties
		self.lar_field_names = list(lar_schema.field)
		self.ts_field_names = list(ts_schema.field)
		self.ts_df, self.lar_df= self.split_ts_row(path=path, data_file=data_file)
		self.state_codes = {'WA':'53', 'WI':'55', 'WV':'54', 'FL':'12', 'WY':'56', 'NH':'33', 'NJ':'34', 'NM':'33', 'NC':'37', 'ND':'38', 'NE':'31', 'NY':'36', 'RI':'44', 'NV':'32', 'CO':'08', 'CA':'06', 'GA':'13', 'CT':'09', 'OK':'40', 'OH':'39',
							'KS':'20', 'SC':'45', 'KY':'21', 'OR':'41', 'SD':'46', 'DE':'10', 'HI':'15', 'PR':'43', 'TX':'48', 'LA':'22', 'TN':'47', 'PA':'42', 'VA':'51', 'VI':'78', 'AK':'02', 'AL':'01', 'AR':'05', 'VT':'50', 'IL':'17', 'IN':'18',
							'IA':'19', 'AZ':'04', 'ID':'16', 'ME':'23', 'MD':'24', 'MA':'25', 'UT':'49', 'MO':'29', 'MN':'27', 'MI':'26', 'MT':'30', 'MS':'29', 'DC':'11'}
		self.results = {}
	#Helper Functions
	def update_results(self, edit_name="", edit_field_results={},  row_type="", row_ids=None, fail_count=None):
		"""Updates the results dictionary by adding a sub-dictionary for the edit, any associated fields, and the result of the edit test.
		edit name is the name of the edit, edit field results is a dict containing field names as keys and pass/fail as values, row type is LAR or TS, 
		row ids contains a list of all rows failing the test"""
		self.results[edit_name] = OrderedDict({})
		self.results[edit_name]["row_type"] = row_type
		if row_ids is not None:
			self.results[edit_name]["fail_ids"] = row_ids
		for field in edit_field_results.keys():
			self.results[edit_name][field] = edit_field_results[field]
			if fail_count is not None:
				self.results[edit_name]["fail_count"] = fail_count

	def results_wrapper(self, fail_df=None, field_name=None, edit_name=None, row_type="LAR"):
		"""Helper function to create results dictionary/JSON object"""
		result={}
		if len(fail_df) > 0:
			count = len(fail_df)
			result[field_name] = "failed"
			if row_type == "LAR":
				failed_rows = list(fail_df.uli)
				self.update_results(edit_name=edit_name, edit_field_results=result, row_type=row_type, row_ids=failed_rows, fail_count=count)
			else:
				self.update_results(edit_name=edit_name, edit_field_results=result, row_type=row_type)
		else:
			result[field_name] = "passed"
			self.update_results(edit_name=edit_name, edit_field_results=result, row_type=row_type)

	def split_ts_row(self, path="../edits_files/", data_file="passes_all.txt"):
		"""This function makes a separate data frame for the TS and LAR portions of a file and returns each as a dataframe."""
		with open(path+data_file, 'r') as infile:
			ts_row = infile.readline().strip("\n")
			ts_data = []
			ts_data.append(ts_row.split("|"))
			lar_rows = infile.readlines()
			lar_data = [line.strip("\n").split("|") for line in lar_rows]
			ts_df = pd.DataFrame(data=ts_data, dtype=object, columns=self.ts_field_names)
			lar_df  = pd.DataFrame(data=lar_data, dtype=object, columns=self.lar_field_names)
		return ts_df, lar_df

	def valid_date(self, date):
		"""checks if a passed date is valid. If not returns false."""
		try:
			time.strptime(date,'%Y%m%d')
			return True
		except:
			return False

	#Edit Rules from FIG
	def s300_1(self):
		"""1) The first row of your file must begin with a 1;."""
		field = "record_id"
		edit_name = "s300_1"
		fail_df = self.ts_df[self.ts_df.record_id!="1"]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="TS")

	def s300_2(self):
		"""2) Any subsequent rows [of your file] must begin with a 2."""
		field = "record_id"
		edit_name = "s300_2"
		fail_df = self.lar_df[self.lar_df.record_id!="2"]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="LAR")

	def s301(self):
		"""The LEI in this row does not match the reported LEI in the transmittal sheet (the first row of your file). Please update your file accordingly."""
		field="LEI"
		edit_name = "s301"
		#get dataframe of LAR row fails
		fail_df = self.lar_df[self.lar_df.lei != self.ts_df.get_value(0, "lei")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="TS")

	def v600(self):
		"""1) The required format for LEI is alphanumeric with 20 characters, and it cannot be left blank."""
		field = "LEI"
		edit_name = "v600"
		#get dataframe of failed LAR rows
		fail_df = self.lar_df[(self.lar_df.lei=="")|(self.lar_df.lei.map(lambda x: len(x))!=20)]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="LAR")

	def s302(self):
		""" The reported Calendar Year does not match the filing year indicated at the start of the filing."""
		field = "calendar_year"
		edit_name = "s302"
		fail_df = self.ts_df[self.ts_df.calendar_year != self.year]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="TS")

	def s304(self):
		"""The reported Total Number of Entries Contained in Submission does not match the total number of LARs in the HMDA file."""
		result={}
		if self.ts_df.get_value(0, "lar_entries") != str(len(self.lar_df)):
			result["lar_entries"] = "failed"
		else:
			result["lar_entries"] = "passed"
		self.update_results(edit_name="s304", edit_field_results=result, row_type="TS/LAR")

	def v601_1(self):
		"""The following data fields are required, and cannot be left blank. A blank value(s) was provided.
		1) Financial Institution Name;
		"""
		field = "inst_name"
		edit_name = "v601_1"
		fail_df = self.ts_df[self.ts_df.inst_name == ""]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="TS")

	def v601_2(self):
		"""The following data fields are required, and cannot be left blank. A blank value(s) was provided.
		2) Contact Person's Name"""
		field = "contact_name"
		edit_name = "v601_2"
		fail_df = self.ts_df[self.ts_df.contact_name == ""]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="TS")

	def v601_3(self):
		"""The following data fields are required, and cannot be left blank. A blank value(s) was provided.
		3) Contact Person's E-mail Address"""
		field = "contact_email"
		edit_name = "v601_3"
		fail_df = self.ts_df[self.ts_df.contact_email == ""]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="TS")

	def v601_4(self):
		"""The following data fields are required, and cannot be left blank. A blank value(s) was provided.
		4) Contact Person's Office Street Address"""
		field = "contact_street_address"
		edit_name = "v601_4"
		fail_df = self.ts_df[self.ts_df.contact_street_address== ""]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="TS")

	def v601_5(self):
		"""The following data fields are required, and cannot be left blank. A blank value(s) was provided.
		5) Contact Person's Office City"""
		field = "office_city"
		edit_name = "v601_5"
		fail_df = self.ts_df[self.ts_df.office_city == ""]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="TS")

	def v602(self):
		"""An invalid Calendar Quarter was reported. 1) Calendar Quarter must equal 4, and cannot be left blank."""
		field = "calendar_quarter"
		edit_name = "v602"
		fail_df = self.ts_df[self.ts_df.calendar_quarter!="4"]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="TS")

	def v603(self):
		"""An invalid Contact Person's Telephone Number was provided.
		1) The required format for the Contact Person's Telephone Number is 999-999-9999, and it cannot be left blank."""
		edit_name = "v603"
		field = "contact_tel"
		fail_df = self.ts_df[(self.ts_df.contact_tel.map(lambda x: len(x))!=12)|(self.ts_df.contact_tel.map(lambda x: x.replace("-","").isdigit())==False)]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="TS")

	def v604(self):
		"""V604 An invalid Contact Person's Office State was provided. Please review the information below and update your file accordingly.
			1) Contact Person's Office State must be a two letter state code, and cannot be left blank."""
		field = "office_state"
		edit_name = "v604"
		#office code is not valid for US states or territories
		fail_df = self.ts_df[~(self.ts_df.office_state.isin(self.state_codes.keys()))]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="TS")

	def v605(self):
		"""V605 An invalid Contact Person's ZIP Code was provided. Please review the information below and update your file accordingly.
			1) The required format for the Contact Person's ZIP Code is 12345-1010 or 12345, and it cannot be left blank."""
		edit_name = "v605"
		field = "office_zip"
		fail_df = self.ts_df[~(self.ts_df.office_zip.map(lambda x: len(x) in (5,10)))|(self.ts_df.office_zip.map(lambda x: x.replace("-","").isdigit())==False)]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="TS")

	def v606(self):
		"""The reported Total Number of Entries Contained in Submission is not in the valid format.
		1) The required format for the Total Number of Entries Contained in Submission is a whole number that is greater than zero, and it cannot be left blank."""
		field = "lar_entries"
		edit_name = "v606"
		fail_df = self.ts_df[(self.ts_df.lar_entries=="")|(self.ts_df.lar_entries.map(lambda x: int(x) <1))|(self.ts_df.lar_entries.map(lambda x: x.isdigit()==False))]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="TS")

	def v607(self):
		"""An invalid Federal Taxpayer Identification Number was provided.
		1) The required format for the Federal Taxpayer Identification Number is 99-9999999, and it cannot be left blank."""
		edit_name = "v607"
		field = "tax_id"
		fail_df = self.ts_df[(self.ts_df.tax_id.map(lambda x: len(x))!=10) | (self.ts_df.tax_id.map(lambda x: x.replace("-","").isdigit())==False)]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df, row_type="TS")

	def s305(self):
		"""A duplicate transaction has been reported. No transaction can be an exact duplicate in a LAR file."""
		edit_name = "s305"
		field = "all"
		#dupe_row = self.lar_df.iloc[0:1] #create dupe row for testing
		#test_df = pd.concat([self.lar_df, dupe_row]) #merge dupe row into dataframe
		fail_df = self.lar_df[self.lar_df.duplicated(keep=False)==True] #pull frame of duplicates
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v608(self):
		"""V608 A ULI with an invalid format was provided.
		1) The required format for ULI is alphanumeric with at least 23 characters and up to 45 characters, and it cannot be left blank."""
		edit_name = "v608"
		field = "ULI"
		#if length not between 23 and 45 or if ULI is blank
		#get subset of LAR dataframe that fails ULI conditions
		fail_df = self.lar_df[((self.lar_df.uli.map(lambda x: len(x))!=23)&(self.lar_df.uli.map(lambda x: len(x))!=45))|(self.lar_df.uli=="")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v609(self):
		"""An invalid ULI was reported. Please review the information below and update your file accordingly.
		1) Based on the check digit calculation, the ULI contains a transcription error."""
		edit_name = "v609"
		field = "ULI"
		check_digit = lar_gen.check_digit_gen #establish check digit function alias
		#get dataframe of check digit failures
		fail_df = self.lar_df[self.lar_df.uli.map(lambda x: str(x)[-2:]) != self.lar_df.uli.map(lambda x: check_digit(ULI=x[:-2]))]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v610_1(self):
		"""V610 An invalid date field was reported.
		1) Application Date must be either a valid date using YYYYMMDD format or NA, and cannot be left blank."""
		edit_name = "v610_1"
		field = "app_date"
		fail_df = self.lar_df[(self.lar_df.app_date!="NA")&(self.lar_df.app_date.map(lambda x: self.valid_date(x))==False)]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v610_2(self):
		"""V610 An invalid date field was reported.
		2) If Action Taken equals 6, then Application Date must be NA, and the reverse must be true."""
		edit_name = "v610_2"
		field = "app_date"
		fail_df = self.lar_df[((self.lar_df.app_date=="NA")&(self.lar_df.action_taken!="6"))|((self.lar_df.action_taken=="6")&(self.lar_df.app_date!="NA"))]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v611(self):
		"""An invalid Loan Type was reported.
		1) Loan Type must equal 1, 2, 3, or 4, and cannot be left blank."""
		edit_name = "v611"
		field = "loan_type"
		fail_df = self.lar_df[~(self.lar_df.loan_type.isin(("1", "2", "3", "4")))]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)


	def v612_1(self):
		"""An invalid Loan Purpose was reported.
		1) Loan Purpose must equal 1, 2, 31, 32, 4, or 5 and cannot be left blank."""
		edit_name = "v612_1"
		field = "loan_purpose"
		fail_df = self.lar_df[~self.lar_df.loan_purpose.isin(("1", "2", "31", "32", "4", "5"))]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v612_2(self):
		"""An invalid Loan Purpose was reported.
		2) If Preapproval equals 1, then Loan Purpose must equal 1."""
		field = "loan_purpose"
		edit_name = "v612_2"
		fail_df = self.lar_df[((self.lar_df.preapproval=="1")&(self.lar_df.loan_purpose!="1"))]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v613_1(self):
		"""An invalid Preapproval data field was provided.
		1) Preapproval must equal 1 or 2, and cannot be left blank."""
		edit_name = "v613_1"
		field = "preapproval"
		fail_df = self.lar_df[~(self.lar_df.preapproval.isin(("1", "2")))]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v613_2(self):
		"""An invalid Preapproval data field was provided.
		2) If Action Taken equals 7 or 8, then Preapproval must equal 1."""
		field = "preapproval"
		edit_name = "v613_2"
		fail_df = self.lar_df[(self.lar_df.action_taken.isin(("7", "8")))&(self.lar_df.preapproval!="1")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v613_3(self):
		"""An invalid Preapproval data field was provided.
		3) If Action Taken equals 3, 4, 5 or 6, then Preapproval must equal 2."""
		field = "preapproval"
		edit_name = "v613_3"
		fail_df = self.lar_df[(self.lar_df.action_taken.isin(("3", "4", "5", "6")))&(self.lar_df.preapproval!="2")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v613_4(self):
		"""An invalid Preapproval data field was provided.
		4) If Preapproval equals 1, then Action Taken must equal 1, 2, 7 or 8."""
		field = "preapproval"
		edit_name = "v613_4"
		fail_df = self.lar_df[(self.lar_df.preapproval=="1")&(~(self.lar_df.action_taken.isin(("1","2","7","8"))))]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v614_1(self):
		"""An invalid Preapproval was provided.
		1) If Loan Purpose equals 2, 4, 31, 32, or 5, then Preapproval must equal 2."""
		field = "preapproval"
		edit_name = "v614_1"
		fail_df = self.lar_df[(self.lar_df.loan_purpose.isin(("2", "4", "31", "32", "5")))&(self.lar_df.preapproval!="2")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)
	def v614_2(self):
		"""An invalid Preapproval was provided.
		2) If Multifamily Affordable Units is a number, then Preapproval must equal 2."""
		field = "preapproval"
		edit_name = "v614_2"
		fail_df = self.lar_df[(self.lar_df.affordable_units.map(lambda x: x.isdigit())==True)&(self.lar_df.preapproval!="2")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)
	def v614_3(self):
		"""An invalid Preapproval was provided.
		3) If Reverse Mortgage equals 1, then Preapproval must equal 2."""
		field = "preapproval"
		edit_name = "v614_3"
		fail_df = self.lar_df[(self.lar_df.reverse_mortgage=="1")&(self.lar_df.preapproval!="2")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)
	def v614_4(self):
		"""An invalid Preapproval was provided.
		4) If Open-End Line of Credit equals 1, then Preapproval must equal 2."""
		field = "preapproval"
		edit_name = "v614_4"
		fail_df = self.lar_df[(self.lar_df.open_end_credit=="1")&(self.lar_df.preapproval!="2")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v615_1(self):
		"""An invalid Construction Method was reported.
		1) Construction Method must equal 1 or 2, and cannot be left blank."""
		field = "const_method"
		edit_name = "v615_1"
		fail_df = self.lar_df[~self.lar_df.const_method.isin(("1","2"))]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v615_2(self):
		"""An invalid Construction Method was reported.
		2) If Manufactured Home Land Property Interest equals 1, 2, 3 or 4, then Construction Method must equal 2."""
		field = "const_method"
		edit_name = "v615_2"
		fail_df = self.lar_df[(self.lar_df.manufactured_interest.isin(("1","2", "3","4")))&(self.lar_df.const_method!="2")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v615_3(self):
		"""An invalid Construction Method was reported.
		3) If Manufactured Home Secured Property Type equals 1 or 2 then Construction Method must equal 2."""
		field = "const_method"
		edit_name = "v615_3"
		fail_df = self.lar_df[(self.lar_df.manufactured_type.isin(("1","2")))&(self.lar_df.const_method!="2")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v616(self):
		"""An invalid Occupancy Type was reported.
		1) Occupancy Type must equal 1, 2, or 3, and cannot be left blank."""
		field = "occupancy"
		edit_name = "v616"
		fail_df = self.lar_df[~(self.lar_df.occ_type.isin(("1","2","3")))]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v617(self):
		"""An invalid Loan Amount was reported.
		1) Loan Amount must be a number greater than 0, and cannot be left blank."""
		field = "loan_amount"
		edit_name = "v617"
		fail_df = self.lar_df.copy()
		fail_df["amount"] = fail_df.loan_amount
		fail_df.amount = fail_df.amount.map(lambda x: 0 if x == "" else x)
		fail_df = fail_df[(fail_df.amount.map(lambda x: int(x))<1)]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v618(self):
		"""An invalid Action Taken was reported.
		1) Action Taken must equal 1, 2, 3, 4, 5, 6, 7, or 8, and cannot be left blank."""
		field = "action_taken"
		edit_name = "v618"
		fail_df = self.lar_df[~(self.lar_df.action_taken.isin(("1","2","3","4","5","6","7","8")))|(self.lar_df.action_taken=="")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v619_1(self):
		"""An invalid Action Taken Date was reported.
		1) Action Taken Date must be a valid date using YYYYMMDD format, and cannot be left blank."""
		field = "action_date"
		edit_name = "v619_1"
		fail_df = self.lar_df[(self.lar_df.action_date=="")|(self.lar_df.action_date.map(lambda x: self.valid_date(x))==False)]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v619_2(self):
		"""An invalid Action Taken Date was reported.
		2) The Action Taken Date must be in the reporting year."""
		field = "action_date"
		edit_name = "v619_2"
		fail_df = self.lar_df[(self.lar_df.action_date.map(lambda x: str(x)[:4])!=self.year)]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v619_3(self):
		"""An invalid Action Taken Date was reported.
		3) The Action Taken Date must be on or after the Application Date."""
		field = "action_date"
		edit_name = "v619_3"
		fail_df = self.lar_df[(self.lar_df.action_date < self.lar_df.app_date)&(self.lar_df.app_date!="NA")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v620(self):
		"""An invalid Street Address was provided.
		1) Street Address cannot be left blank."""
		field = "street_address"
		edit_name = "v620"
		fail_df = self.lar_df[(self.lar_df.street_address=="")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v621(self):
		"""An invalid City was provided.
		1) City cannot be left blank."""
		field = "city"
		edit_name = "v621"
		fail_df = self.lar_df[(self.lar_df.city=="")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v622_1(self):
		"""An invalid City, State and/or Zip Code were provided.
		1) If Street Address was not reported NA, then City, State, and Zip Code must be provided, and not reported NA."""
		field = "city"
		edit_name = "v622_1"
		fail_df = self.lar_df[(self.lar_df.street_address!="NA")&(self.lar_df.city=="NA")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v622_2(self):
		"""An invalid City, State and/or Zip Code were provided.
		1) If Street Address was not reported NA, then City, State, and Zip Code must be provided, and not reported NA."""
		field = "state"
		edit_name = "v622_2"
		fail_df = self.lar_df[(self.lar_df.street_address!="NA")&(self.lar_df.state=="NA")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v622_3(self):
		"""An invalid City, State and/or Zip Code were provided.
		1) If Street Address was not reported NA, then City, State, and Zip Code must be provided, and not reported NA."""
		field = "zip_code"
		edit_name = "v622_3"
		fail_df = self.lar_df[(self.lar_df.street_address!="NA")&(self.lar_df.zip_code=="NA")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v623(self):
		"""An invalid State was provided.
		1) State must be either a two letter state code or NA, and cannot be left blank."""
		field = "state"
		edit_name = "v623"
		fail_df = self.lar_df[~(self.lar_df.state.isin(self.state_codes))|(self.lar_df.state=="NA")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v624(self):
		"""An invalid Zip Code was provided.
		1) The required format for Zip Code is 12345-1010 or 12345 or NA, and it cannot be left blank."""
		field = "zip_code"
		edit_name = "v624"
		fail_df = self.lar_df[((self.lar_df.zip_code.map(lambda x: len(x) not in (10, 5)))|(self.lar_df.zip_code.map(lambda x: x.replace("-","").isdigit())==False))
		&(self.lar_df.zip_code!="NA")]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v625_1(self):
		"""An invalid Census Tract was provided.
		1) The required format for Census Tract is an eleven digit number or NA, and it cannot be left blank."""
		field = "tract"
		edit_name = "v625_1"
		fail_df = self.lar_df[(self.lar_df.tract!="NA")&((self.lar_df.tract.map(lambda x: len(x)!=11))|(self.lar_df.tract.map(lambda x: x.isdigit())==False))]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v625_2(self):
		"""An invalid Census Tract was provided.
		2) If Census Tract is not reported NA, then the number provided must be a valid census tract number defined by the U.S. Census Bureau."""
		field = "tract"
		edit_name = "v625_2"
		fail_df = self.lar_df[(self.lar_df.tract!="NA")&(~self.lar_df.tract.isin(self.tracts))]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v626(self):
		"""v626 An invalid County was provided.
		1) The required format for County is a five digit FIPS code or NA, and it cannot be left blank"""
		field = "county"
		edit_name = "v626"
		fail_df = self.lar_df[(self.lar_df.county!="NA")&((self.lar_df.county.map(lambda x: len(x))!=5)|(self.lar_df.county.map(lambda x: x.isdigit())==False))]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)

	def v627(self):
		"""An invalid Census Tract or County was provided.
		1) If County and Census Tract are not reported NA, they must be a valid combination of information.
		The first five digits of the Census Tract must match the reported five digit County FIPS code."""
		field = "tract/county"
		edit_name = "v627"
		fail_df = self.lar_df[((self.lar_df.county!="NA")&(self.lar_df.tract!="NA"))&(self.lar_df.tract.map(lambda x: str(x)[:5])!=self.lar_df.county)]
		self.results_wrapper(edit_name=edit_name, field_name=field, fail_df=fail_df)