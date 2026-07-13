# KPI Mapping

This document maps course conversion analytics columns to business KPIs used by analysts and stakeholders. The goal is to explain learner demand, preview interest, enrollment success, and drop-off across the search-to-enrollment funnel.

## 1. Total Searches

| Field | Detail |
| --- | --- |
| Formula | `COUNT(search_query)` |
| Related Columns | `search_query`, `search_time`, `user_id` |
| Business Importance | Measures learner demand and the volume of discovery activity on the platform. |
| Update Frequency | Daily |
| Notes | Blank or null search terms should be excluded from search demand reporting. |

## 2. Unique Searchers

| Field | Detail |
| --- | --- |
| Formula | `COUNT(DISTINCT user_id)` from search logs |
| Related Columns | `user_id`, `search_query`, `search_time` |
| Business Importance | Shows how many learners are actively using search, not just how many searches were submitted. |
| Update Frequency | Daily |
| Notes | Useful for separating broad demand from repeated searches by the same learner. |

## 3. Course Preview Rate

| Field | Detail |
| --- | --- |
| Formula | `COUNTIF(preview_clicked = True)` |
| Related Columns | `course_id`, `preview_clicked`, `preview_time`, `user_id` |
| Business Importance | Measures learner interest after courses appear in discovery or search results. |
| Update Frequency | Daily |
| Notes | `False` preview events should not be counted as successful preview clicks. |

## 4. Enrollment Rate

| Field | Detail |
| --- | --- |
| Formula | `COUNT(enrollment_id)` or `COUNTIF(enrollment_status = 'active')` depending on reporting definition |
| Related Columns | `enrollment_id`, `course_id`, `user_id`, `enrollment_status`, `enrollment_date` |
| Business Importance | Tracks how many learners move from interest to enrollment. |
| Update Frequency | Daily |
| Notes | Business reporting should clarify whether pending and cancelled enrollments are included. |

## 5. Conversion Rate

| Field | Detail |
| --- | --- |
| Formula | `(Active Enrollments / Preview Clicks) * 100` |
| Related Columns | `preview_clicked`, `course_id`, `user_id`, `enrollment_status`, `enrollment_id` |
| Business Importance | Measures how effectively course interest becomes active enrollment. |
| Update Frequency | Daily |
| Notes | Join preview and enrollment activity by `user_id` and `course_id`; count only `preview_clicked = True` in the denominator. |

## 6. Category Performance

| Field | Detail |
| --- | --- |
| Formula | `COUNT(enrollment_id) GROUP BY category` |
| Related Columns | `category`, `course_id`, `enrollment_status`, `enrollment_id` |
| Business Importance | Identifies high-performing learning categories and helps prioritize content investment. |
| Update Frequency | Weekly and monthly |
| Notes | Category names must be standardized before grouping. |

## 7. Course Popularity

| Field | Detail |
| --- | --- |
| Formula | `COUNTIF(preview_clicked = True) GROUP BY course_id` |
| Related Columns | `course_id`, `course_name`, `preview_clicked`, `preview_time` |
| Business Importance | Shows which courses receive the most learner attention before enrollment. |
| Update Frequency | Daily |
| Notes | High popularity with low conversion may indicate pricing, course detail, rating, or content mismatch issues. |

## 8. Price Conversion Impact

| Field | Detail |
| --- | --- |
| Formula | `Conversion Rate GROUP BY price band` |
| Related Columns | `price`, `course_id`, `preview_clicked`, `enrollment_status` |
| Business Importance | Helps determine whether pricing is a barrier to enrollment. |
| Update Frequency | Weekly |
| Notes | Recommended price bands: free, low, mid, and premium. |
