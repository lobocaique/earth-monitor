from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window
from pyspark.sql.types import StructType, StringType, DoubleType

# Schema of the JSON data
schema = StructType() \
    .add("shipment_id", StringType()) \
    .add("location", StringType()) \
    .add("status", StringType()) \
    .add("timestamp", DoubleType()) \
    .add("meta", StringType())

def main():
    spark = SparkSession \
        .builder \
        .appName("EcoLogisticsProcessor") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    # Read from Kafka
    # Note: 'kafka' is the host alias in docker-compose network
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:29092") \
        .option("subscribe", "logistics_events") \
        .load()

    # Parse JSON
    parsed_df = df.select(from_json(col("value").cast("string"), schema).alias("data")).select("data.*")

    # Simple Aggregation: Count events by location (running count)
    agg_df = parsed_df.groupBy("location").count()

    # Output to Console
    query = agg_df \
        .writeStream \
        .outputMode("complete") \
        .format("console") \
        .start()

    query.awaitTermination()

if __name__ == "__main__":
    main()
