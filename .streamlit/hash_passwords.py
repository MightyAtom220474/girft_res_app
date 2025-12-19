##########################################################################
# only run this file once when initially setting up the hashed passwords #
##########################################################################

from werkzeug.security import generate_password_hash
import data_store as ds

ds.load_or_refresh_all()
temp_password = "Temporary123!"
ds.staff_list["password"] = ds.staff_list["username"].apply(
    lambda u: generate_password_hash(temp_password)
)
ds.staff_list["must_change_password"] = True
ds.staff_list.to_csv("staff_list.csv", index=False)