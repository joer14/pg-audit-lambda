## PG Audit Setup

Included in the tools repo is a utility script that will automatically install `pgaudit` on RDS.

To use the default session logging (not object based logging, but log everything) you can use the `install_pg_audit.py` utility in the `tools` directory.

The key assumption with this tool is that you are using the default parameter group that is created when you create your database on RDS.

Adapted from the following [AWS Docs](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.PostgreSQL.CommonDBATasks.html#Appendix.PostgreSQL.CommonDBATasks.Auditing), except using session based logging instead of object based logging.\
