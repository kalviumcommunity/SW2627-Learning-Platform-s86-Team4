# Column Relationships

This document explains how columns connect across the course conversion analytics datasets and how those relationships support business analysis.

## 1. Search to Preview

| Field | Detail |
| --- | --- |
| Definition | Searches that lead to course preview clicks by the same learner. |
| Related Columns | `user_id`, `search_query`, `search_time`, `course_id`, `preview_clicked`, `preview_time` |
| Relationship Logic | Link search and preview events by `user_id`, then compare `search_time` and `preview_time` to understand whether preview activity followed search activity. |
| Business Impact | Measures how effectively search behavior leads to course interest. |

## 2. Search to Enrollment

| Field | Detail |
| --- | --- |
| Definition | Learner searches that eventually lead to enrollment activity. |
| Related Columns | `user_id`, `search_query`, `search_time`, `course_id`, `enrollment_status`, `enrollment_date` |
| Relationship Logic | Connect search logs to enrollments by `user_id` and sequence events using `search_time` and `enrollment_date`. |
| Business Impact | Measures whether learner intent is being converted into enrollment outcomes. |

## 3. Course Popularity

| Field | Detail |
| --- | --- |
| Definition | Preview clicks grouped by course. |
| Related Columns | `course_id`, `course_name`, `preview_clicked`, `preview_time` |
| Relationship Logic | Join `preview_logs.course_id` to `courses.course_id` and count records where `preview_clicked = True`. |
| Business Impact | Identifies highly viewed courses and courses that may need stronger conversion support. |

## 4. Conversion Funnel

| Field | Detail |
| --- | --- |
| Definition | Learner journey from search to preview to enrollment. |
| Funnel | Search -> Preview -> Enrollment |
| Related Columns | `user_id`, `search_query`, `search_time`, `course_id`, `preview_clicked`, `preview_time`, `enrollment_status`, `enrollment_date` |
| Relationship Logic | Use `user_id` to follow learner actions and `course_id` to connect previewed courses to enrolled courses. |
| Business Impact | Identifies learner drop-off and shows where the platform loses potential enrollments. |

## 5. Category Conversion

| Field | Detail |
| --- | --- |
| Definition | Enrollment and conversion performance grouped by learning category. |
| Related Columns | `category`, `course_id`, `preview_clicked`, `enrollment_status`, `enrollment_id` |
| Relationship Logic | Join course metadata to preview and enrollment data through `course_id`, then group by `category`. |
| Business Impact | Measures which learning categories convert well and which need content, pricing, or discovery improvements. |

## 6. Rating and Conversion

| Field | Detail |
| --- | --- |
| Definition | Relationship between course learner rating and preview-to-enrollment conversion. |
| Related Columns | `rating`, `course_id`, `preview_clicked`, `enrollment_status`, `enrollment_id` |
| Relationship Logic | Join courses to preview and enrollment data by `course_id`, then compare conversion rates by rating bands. |
| Business Impact | Helps assess whether course quality perception influences enrollment decisions. |

## 7. Price and Conversion

| Field | Detail |
| --- | --- |
| Definition | Relationship between course price and enrollment conversion. |
| Related Columns | `price`, `course_id`, `preview_clicked`, `enrollment_status`, `enrollment_id` |
| Relationship Logic | Group courses into price bands and compare active enrollments against preview clicks. |
| Business Impact | Helps identify whether price is creating friction after learners preview a course. |
