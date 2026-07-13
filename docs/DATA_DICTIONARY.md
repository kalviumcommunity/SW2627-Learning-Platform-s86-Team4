# Course Conversion Analytics Data Dictionary

## Dataset Overview

| Attribute | Detail |
| --- | --- |
| Purpose | Provide a business-ready view of learner search, course preview, and enrollment behavior for the Course Conversion Analytics Dashboard. |
| Business Problem | The platform has highly viewed courses that do not always convert into active enrollments. These datasets help identify where learners drop off and which course attributes may influence conversion. |
| Source | Platform course catalog, search event logs, preview event logs, and enrollment records. In this repo, enrollment records are currently stored in `data/raw/enrollments.json`; the logical dataset is documented as enrollments. |
| Refresh Frequency | Daily for event logs and enrollment records; as needed for course catalog changes. |
| Maintained By | Data Analytics Team / Learning Platform Analytics Owner. |

## Dataset Files

| Dataset | Grain | Primary Purpose |
| --- | --- | --- |
| `courses.csv` | One row per course | Course metadata used to segment and explain conversion performance. |
| `search_logs.csv` | One row per learner search event | Learner demand and search intent tracking. |
| `preview_logs.csv` | One row per course preview event | Learner interest and course popularity tracking. |
| `enrollments` | One row per enrollment record | Enrollment outcome and conversion tracking. |

## `courses.csv`

| Column | Type | Business Meaning | Example | Valid Values | Null Handling | Related KPI | Update Frequency | Key Info | Constraints | Business Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `course_id` | String | Unique course identifier used to connect catalog data with previews and enrollments. | `C002` | Course IDs in platform catalog | Not nullable | Course Preview Rate, Enrollment Rate, Conversion Rate | When courses are added or changed | Primary key; foreign key in preview and enrollment data | Should follow stable ID format such as `C###` | Required for all course-level joins. |
| `course_name` | String | Human-readable course title shown to learners. | `Data Analysis with Pandas` | Valid platform course titles | Should not be null for published courses | Course Popularity, Conversion Rate | When catalog changes | Descriptive attribute | Should be clean and stakeholder readable | Useful for dashboards, but joins should use `course_id`. |
| `category` | String | Learning subject area assigned to the course. | `Data Science` | Standardized course categories | Nulls should be mapped to `Unknown` only for reporting | Category Performance | When catalog changes | Descriptive attribute | Use controlled vocabulary | Recommended clearer name: `course_category`. |
| `instructor` | String | Instructor responsible for delivering the course. | `Sana Patel` | Instructor names from platform records | Nulls should be investigated | Instructor Performance | When course ownership changes | Descriptive attribute | Should align with instructor master data if available | Supports instructor-level content analysis. |
| `price` | Decimal | Listed course price in platform currency. | `29.99` | Numeric values greater than or equal to 0 | Nulls should be treated as missing pricing data | Price Conversion Impact | When pricing changes | Descriptive metric | Do not include currency symbols | `0.00` represents a free course. |
| `rating` | Decimal | Average learner rating for the course. | `4.8` | 0.0 to 5.0 | May be null for new or unrated courses | Course Rating Analysis | As ratings are refreshed | Descriptive metric | Must stay within rating scale | Recommended clearer name: `course_rating`. |

## `search_logs.csv`

| Column | Type | Business Meaning | Example | Valid Values | Null Handling | Related KPI | Update Frequency | Key Info | Constraints | Business Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `user_id` | String | Learner or platform user who submitted the search. | `U001` | Valid learner user IDs | Not nullable for funnel analysis | Unique Searchers, Search-to-Preview Rate | Daily | Foreign key to user master data if available | Should not expose direct personal information | Links learner behavior across search, preview, and enrollment. |
| `search_query` | String | Text entered by the learner in search. | `python pandas tutorial` | Free-text search terms | Blank or null values should be excluded from demand analysis | Total Searches | Daily | Event attribute | Trim whitespace and normalize casing for keyword analysis | Indicates learner demand and intent. |
| `search_time` | Datetime | Timestamp when the search was submitted. | `2026-07-10T08:12:34` | ISO 8601 datetime | Nulls should be rejected for time-series reporting | Daily Search Trend, Search-to-Preview Rate | Daily | Event timestamp | Use one reporting timezone consistently | Supports funnel sequencing and daily reporting. |

## `preview_logs.csv`

| Column | Type | Business Meaning | Example | Valid Values | Null Handling | Related KPI | Update Frequency | Key Info | Constraints | Business Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `user_id` | String | Learner or platform user associated with a preview event. | `U001` | Valid learner user IDs | Not nullable | Course Preview Rate, Conversion Rate | Daily | Foreign key to user master data if available | Should be consistent with search and enrollment logs | Used to connect interest to later enrollment. |
| `course_id` | String | Course that was previewed or evaluated in the preview event. | `C002` | Course IDs in `courses.csv` | Not nullable | Course Popularity, Conversion Rate | Daily | Foreign key to `courses.course_id` | Must exist in course catalog for complete reporting | Enables course-level popularity analysis. |
| `preview_clicked` | Boolean | Whether the learner clicked or opened a course preview. | `True` | `True`, `False` | Nulls should be treated as invalid event data | Course Preview Rate, Conversion Rate | Daily | Event flag | Count only `True` for preview clicks | Do not confuse with impressions or search result appearances. |
| `preview_time` | Datetime | Timestamp when the preview event was recorded. | `2026-07-10T08:13:02` | ISO 8601 datetime | Nulls should be rejected for funnel sequencing | Conversion Funnel Drop-off | Daily | Event timestamp | Should be after related search activity when a search exists | Used to measure time from interest to enrollment. |

## `enrollments`

| Column | Type | Business Meaning | Example | Valid Values | Null Handling | Related KPI | Update Frequency | Key Info | Constraints | Business Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `enrollment_id` | String | Unique identifier for an enrollment record. | `E1001` | Enrollment IDs generated by platform | Not nullable | Enrollment Rate, Conversion Rate | Daily | Primary key | Should be unique and stable | Represents enrollment record, not necessarily successful active enrollment. |
| `user_id` | String | Learner associated with the enrollment. | `U001` | Valid learner user IDs | Not nullable | Enrollment Rate, Conversion Rate | Daily | Foreign key to user master data if available | Must align with event logs for funnel analysis | Connects enrollment outcome to prior search and preview behavior. |
| `course_id` | String | Course associated with the enrollment. | `C002` | Course IDs in `courses.csv` | Not nullable | Enrollment Rate, Category Performance | Daily | Foreign key to `courses.course_id` | Must exist in course catalog for category analysis | Enables course and category enrollment reporting. |
| `enrollment_status` | String | Current state of the enrollment record. | `active` | `active`, `pending`, `cancelled`; optionally `completed` if supported | Nulls should be treated as unknown and excluded from active conversion counts | Active Enrollments, Conversion Rate | Daily or when status changes | Status attribute | Define which statuses count as conversion | Active status usually represents successful conversion. |
| `enrollment_date` | Datetime | Timestamp when the enrollment record was created or confirmed. | `2026-07-10T09:00:00` | ISO 8601 datetime | Nulls should be rejected for time-series reporting | Daily Enrollments, Conversion Rate | Daily | Event timestamp | Should not precede related preview event for same learner and course | Used to measure time from preview to enrollment. |

## Recommended Join Paths

| Analysis | Join Logic |
| --- | --- |
| Course preview performance | `preview_logs.course_id = courses.course_id` |
| Course enrollment performance | `enrollments.course_id = courses.course_id` |
| Learner funnel behavior | Match `search_logs.user_id`, `preview_logs.user_id`, and `enrollments.user_id`; use timestamps for sequencing. |
| Course conversion | Join preview and enrollment records by `user_id` and `course_id`; compare `preview_clicked = True` to active enrollments. |
| Category performance | Join course metadata to enrollment and preview records using `course_id`, then group by `category`. |

## Documentation Standards

- Use `course_id` for joins instead of `course_name`.
- Count only `preview_clicked = True` as a preview click.
- Count only clearly successful statuses, usually `enrollment_status = 'active'`, for active conversion KPIs.
- Standardize category names before grouping.
- Store all event timestamps in a consistent timezone and ISO 8601 format.
- Keep ambiguous names documented until they can be renamed in the data pipeline.
