from uuid import UUID
from sample_data_schema import *
from fluvius.data.data_model import DataClassModel, field, NamespaceModel

class SampleDataAccessManager(DataAccessManager):
    __connector__ = SQLiteConnector
    __auto_model__ = True


sample_data_access_manager = SampleDataAccessManager()

@SampleDataAccessManager.register_model('company')
class CompanyModel(NamespaceModel):
    pass

# class CompanyModel(DataModel):
#     _id: UUID
#     system_entity: str
#     business_name: str
#     name: str
#     tax_id: str
#     group_npi: str
#     description: str
#     company_code: str

#     active: bool
#     owner_id: str
#     default_signer_id: str
#     verified_tax_id: str
#     verified_npi: str
#     user_tag: str
#     system_tag: str
#     status: CompanyStatus
#     kind: CompanyType
#     invitation_code: str
