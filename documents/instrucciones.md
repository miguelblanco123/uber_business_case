Business Case: Predictive Analytics & Dashboarding for
ATD Optimization
At Uber Eats, delivering food at the right time isn’t just about logistics — it’s about trust. Every
late delivery risks a poor customer experience, while every minute of inefficiency affects the
bottom line. In a marketplace defined by real-time demand, weather variability, and courier
availability, understanding and improving delivery accuracy is a constant challenge — and a
major opportunity.
In this business case, you will take on the role of an Automation & Analytics team member to
help tackle this challenge through data. Your task is to design and implement a complete
analytics workflow that begins with extracting and transforming weekly delivery data, continues
with building a Streamlit dashboard to monitor and explore delivery patterns, and optionally
includes a predictive model for Actual Time of Delivery (ATD) to support operational forecasting.
This case is designed to evaluate your ability to work with complex datasets, follow best
practices in Python and SQL, and build clear, actionable tools that can inform decision-making.
Your work will directly support teams responsible for dispatch planning, courier incentives, and
ETA reliability — contributing to smarter, data-driven operations at scale.
Specific Tasks
1. Data Extraction:
You will be provided with a set of tables and corresponding columns. Your first task is to
develop an efficient SQL query that extracts the required data and establishes a pipeline
to produce a dataset similar to the one attached to this case. The query should
dynamically calculate the date range for the previous week based on the current date
({{ds}}), and be designed to refresh on a weekly basis. The final output should be
saved to a table within the AA_tables schema.
2. Streamlit Dashboard:
Once the data is prepared, you will create an interactive and user-friendly dashboard
using Streamlit. The dashboard should present key metrics and the results of the
predictive model in a clear and actionable format. It should enable stakeholders to
explore delivery time predictions and other relevant operational insights.
3. (Bonus) Predictive Model for ATD:
As an optional enhancement, you will build a predictive model for ATD (Actual Time of
Delivery). The model should leverage the prepared dataset to accurately forecast
delivery times, enabling Uber to improve delivery accuracy and operational efficiency.
Presentation Requirement (5–10 Slides)
You will be expected to summarize your findings and recommendations in a 5–10 slide
presentation tailored for a non-technical business audience (still keep in mind that you will need
to share and explain your technical expertise in a clear manner) and present it in a Business
Panel. The goal is to ensure stakeholders can draw clear conclusions and take action based on
your work.
The presentation should include:
● Business context and problem statement
● Summary of methodology (data sources, pipeline, model, dashboard)
● Key findings and insights
● Strategic implications and recommendations
● Suggested execution next steps for operational teams
1.- Data extraction
Using the tables in the Appendix 1, you must write an SQL query that meets the following:
✅ Requirements:
1. Dispatch Metrics: Use the tables on the Appendix 1
delivery_matching.eats_dispatch_metrics_job_message and
tmp.lea_trips_scope_atd_consolidation_v2 to obtain metrics for the delivery trips,
including trip identifiers (workflow_uuid, driver_uuid, delivery_trip_uuid), order dates, and
the pickup and delivery distances (pickupdistance, traveldistance), ensuring the
distances are in kilometers.
2. Filtering by Country: Filter the results to only show the metrics for Mexico.
3. Distance Calculations: Distances should be converted from meters to kilometers by
dividing by 1,000.
🔁 Submission:
The final output should look like the table on the Appendix 2.
Also describe the workflow that you would create to maintain this table refreshed. This
workflow should dynamically calculate the date range for the previous week based on the
current execution date. Use the current date ({{ds}}) to adjust the query and select the relevant
data for the previous week. Code is not necessary in this task, you need to create a rough draft
on how you´ll design this workflow and what tasks this workflow should contain.
● The final result expected here should be an SQL query that can pull data structured
like the dataset attached that it's going to be used in the next steps.
2.- Streamlit Dashboard Development
As part of the evaluation process, we are asking you to develop a Streamlit dashboard
focused on data analysis. The goal is to assess your ability to structure Python code
professionally, apply best practices, and build an intuitive, functional dashboard.
✅ Requirements:
● Dashboard:
Create a Streamlit dashboard that showcases data analysis from the data received.
While you have freedom regarding the visual style, keep in mind that clarity and usability
of the visual elements will also be considered. The primary focus remains on
functionality, code quality, and structure — but a clean, readable interface is a plus.
● Python Best Practices:
Code should follow Python best practices, including modularization (a plus), clean code
principles, and logical organization.
● Flake8 Integration:
The codebase must be Flake8-compliant
● Documentation:
The GitHub repository must include:
○ A clear and concise README.md file with:
■ Overview of the project and dataset used
■ Setup instructions (e.g., how to install dependencies and run the app)
■ Any additional notes for reviewers
○ A requirements.txt file to install all dependencies
● Reproducibility:
The dashboard should be easily reproducible by any team member. Make sure all
necessary files, configs, and instructions are included.
🔁 Submission:
Please share a link to your public GitHub repository once you’ve completed the task.
● The dashboard does not need to follow any specific structure, but it should present a
coherent analysis that justifies the data approaches taken and the modeling decisions
made, if any. The final result should reflect analytical thinking and provide meaningful
insights based on the data.
3.- (Bonus) Predictive Model for Actual Time of Delivery (ATD)
In this section, you are expected to build and deliver a predictive model that estimates the
Actual Time of Delivery (ATD). This model will be a key component of Uber’s efforts to
improve delivery time accuracy and operational efficiency. Please address each of the following
tasks:
✅ Requirements:
1. Target Definition
How would you define and compute the target variable (ATD) using the available timestamps in
the dataset?
– Clearly describe the formula you would use and provide a brief example to illustrate how it
works in practice.
2. Data Cleaning and Preprocessing
What data-cleaning and preprocessing steps would you apply to prepare the dataset for
modeling?
– Outline your approach for handling missing values, timestamp parsing, outlier removal, unit
standardization, and relevant filtering logic. Be sure to explain how your process ensures a
clean and reliable dataset.
3. Feature Engineering
Which features would you derive from the raw data, and why?
– List the engineered features (e.g., time-based, weather-related, operational, geographic) and
explain the rationale behind each. Clarify how these features are expected to influence delivery
times.
4. Model Selection and Training
Which modeling algorithms would you evaluate for predicting ATD, and why?
– Justify your selection based on the problem type, business context, and available data.
Discuss the trade-offs between simplicity, accuracy, and interpretability, and describe how you
would train and compare model performance.
5. Data Splitting and Validation Strategy
How would you split your dataset for training and validation?
– Describe your strategy to prevent data leakage, particularly considering the time-dependent
nature of delivery data. Justify why your chosen method supports a realistic and robust
evaluation of the model.
6. Evaluation Metrics
Which metrics would you report to evaluate your model’s performance, and why?
– Discuss the strengths and limitations of each metric in the context of delivery prediction and
stakeholder expectations.
7. Integration into Pipeline and Dashboard
How would you integrate your model into a weekly ETL pipeline and a Streamlit dashboard?
– Provide a short plan or diagram outlining when the model should run, how predictions would
be stored, and how the dashboard would consume them. Emphasize scalability, maintainability,
and usability for operations teams.
🔁 Submission:
● A clear explanation for each of the above points
● Your final Python code (in .py or notebook format)
● A README.md explaining how to run the pipeline, train the model, and launch the
dashboard
● Optional: a deployed or locally runnable version of the Streamlit app for demo purposes
APPENDIX 1
1. Table: dwh.dim_city
This table contains information about cities in Latin America. It must be included in the query to
correctly assign cities to regions and territories.
Column Description
city_id Unique identifier for the city.
city_name Name of the city.
country_name Name of the country the city belongs to (e.g., Mexico,
Brazil).
mega_region The broader region the city belongs to (e.g., LatAm).
currency_code Currency code used in the country of the city (e.g., MXN,
USD).
population_size Size of the city's population.
average_income Average income in the city.
2. Table: kirby_external_data.cities_strategy_region
This table contains additional information about cities, specifically about the regions and
territories within each country.
Column Description
city_id Unique identifier for the city.
region The region the city belongs to (e.g., "North Mexico", "South Brazil").
territory More specific territory within the region (e.g., "MexicoWest").
population_size Size of the population in the region.
market_demand Market demand in the region.
3. Table: delivery_matching.eats_dispatch_metrics_job_message
Contains the metrics for delivery trips, including distances and order information.
Column Description
jobuuid Unique identifier for the delivery job.
cityid Identifier for the city associated with the delivery job.
datestr Date and time the delivery job was performed.
pickupdistance Pickup distance in meters (must be converted to kilometers).
traveldistance Delivery distance in meters (must be converted to kilometers).
isfinalplan Indicator of whether the job is part of the final delivery plan
(boolean).
estimated_delivery_tim
e
Estimated delivery time.
delivery_status Status of the delivery (completed, pending).
4. Table: tmp.lea_trips_scope_atd_consolidation_v2
Contains consolidated information about delivery trips and drivers.
Column Description
delivery_trip_uuid Unique identifier for the delivery trip.
workflow_uuid Unique identifier for the workflow or order.
driver_uuid Unique identifier for the driver or courier associated
with the delivery trip.
courier_flow Type of vehicle or medium used for the delivery (e.g.,
"Motorbike").
restaurant_offered_timestamp_ut
c
UTC time when the restaurant received the order.
order_final_state_timestamp_loca
l
Local time when the order reached its final state
(completed).
eater_request_timestamp_local Local time when the customer made the delivery
request.
geo_archetype Type of geolocation associated with the order (e.g.,
"Drive momentum").
merchant_surface Device used by the restaurant to process the order
(e.g., "Tablet").
total_distance_travelled Total distance traveled by the driver.
APPENDIX 2
Column Description
territory Type: str (String).
Description: A subdivision within a region that
denotes a more specific zone, such as a territorial
division or operational area.
country_name Type: str (String).
Description: The name of the country where the
delivery or service is being performed, represented by
its common name.
workflow_uuid Type: str (String).
Description: A unique global identifier (UUID)
assigned to a specific workflow, used to track an
order or process within the system.
driver_uuid Type: str (String).
Description: A unique global identifier (UUID)
assigned to the driver or courier responsible for
completing the delivery or task related to the
workflow.
delivery_trip_uuid Type: str (String).
Description: A unique global identifier (UUID)
associated with a specific delivery trip within a
workflow.
courier_flow Type: str (String).
Description: The type of transport used by the
courier to complete the delivery, such as "Motorbike",
"Car", etc.
restaurant_offered_timestamp_ut
c
Type: timestamp (UTC timestamp).
Description: The date and time in UTC when the
restaurant received the order and began processing
it.
order_final_state_timestamp_loca
l
Type: timestamp (Local timestamp).
Description: The local date and time when the order
reached its final state, for example, when the delivery
was completed or the order reached its final status.
eater_request_timestamp_local Type: timestamp (Local timestamp).
Description: The local date and time when the
customer made the delivery request, i.e., when the
order was created.
geo_archetype Type: str (String).
Description: The type of geolocation associated with
the order, defined as a strategic region for marketing
efforts.
merchant_surface Type: str (String).
Description: The type of device or interface used by
the merchant (restaurant) to interact with the system,
such as "Tablet", "Phone", etc.
pickup_distance Type: float (Floating point number).
Description: The distance in kilometers from the
restaurant to the pickup point of the order.
dropoff_distance Type: float (Floating point number).
Description: The distance in kilometers from the
pickup point to the final delivery destination, such as
the customer's address.
ATD (Actual Time of Delivery) Type: float (Floating point number).
Description: The total time, in minutes, it takes from
when the order is rest offered
(restaurant_offered_timestamp_utc)until it is
delivered to the final destination
(order_final_state_timestamp). This is a measure of
the total delivery time, including both preparation and
transit time.