"""Start one Spark session so Ivy caches the Kafka connector inside the image."""

from pyspark.sql import SparkSession

spark = (
    SparkSession.builder.master("local[1]")
    .appName("warmup")
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3")
    .getOrCreate()
)
spark.range(1).count()
spark.stop()
print("jars cached")
