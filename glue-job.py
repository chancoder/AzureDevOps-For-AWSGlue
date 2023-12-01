import sys
import datetime
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql.functions import udf
from pyspark.sql.types import IntegerType

def sparkSqlQuery(glueContext, query, mapping, transformation_ctx) -> DynamicFrame:
    for alias, frame in mapping.items():
        frame.toDF().createOrReplaceTempView(alias)
    result = spark.sql(query)
    return DynamicFrame.fromDF(result, glueContext, transformation_ctx)
args = getResolvedOptions(sys.argv, ["JOB_NAME"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# Load data from the Glue Data Catalog
AWSGlueDataCatalog_node1701169635451 = glueContext.create_dynamic_frame.from_catalog(
    database="real_estate_analysis",
    table_name="property_listings",
    transformation_ctx="AWSGlueDataCatalog_node1701169635451",
)

# Transformation: Calculate house age and normalize SQUARE_FEET
current_year = datetime.datetime.now().year
calc_age_udf = udf(lambda year: current_year - year, IntegerType())

# Convert to DataFrame for transformation
df = AWSGlueDataCatalog_node1701169635451.toDF()
df = df.withColumn("house_age", calc_age_udf(df["year_built"]))
df = df.withColumn("square_feet", df["square_feet"].cast(IntegerType()))

# Convert back to DynamicFrame for Glue operations
transformed_dyf = DynamicFrame.fromDF(df, glueContext, "transformed_dyf")

# SQL Query for analysis
sql_query = """
SELECT garage_spaces, AVG(price) as avg_price, AVG(house_age) as avg_age, AVG(square_feet) as avg_square_feet
FROM myDataSource
GROUP BY garage_spaces
"""
# Execute SQL Query
SQLQuery_node = sparkSqlQuery(
    glueContext,
    query=sql_query,
    mapping={"myDataSource": transformed_dyf},
    transformation_ctx="SQLQuery_node",
)

# Write results to S3 in Parquet format
sink_node = glueContext.write_dynamic_frame.from_options(
    frame=SQLQuery_node,
    connection_type="s3",
    connection_options={"path": "s3://glue-devops-blog/results"},
    format="parquet",
    transformation_ctx="sink_node"
)

job.commit()