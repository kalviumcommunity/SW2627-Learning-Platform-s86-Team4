# Ambiguous Columns

This document identifies columns that can be misread by analysts or business stakeholders if they are not documented clearly.

## 1. `category`

| Field | Detail |
| --- | --- |
| Why It Is Ambiguous | Could refer to a learning category, business department, marketing segment, or learner group. |
| Resolved Meaning | The subject area assigned to a course. |
| Business Interpretation | Used to compare discovery, preview, enrollment, and conversion across learning domains. |
| Suggested Better Name | `course_category` |
| Risk If Misunderstood | Category performance reports may group courses incorrectly or mix product taxonomy with business departments. |

## 2. `rating`

| Field | Detail |
| --- | --- |
| Why It Is Ambiguous | Could mean learner rating, instructor rating, internal quality score, or platform recommendation score. |
| Resolved Meaning | Average learner rating for the course. |
| Business Interpretation | Indicates learner satisfaction and perceived course quality. |
| Suggested Better Name | `course_rating` |
| Risk If Misunderstood | Analysts may incorrectly attribute rating changes to instructor performance or recommendation ranking. |

## 3. `price`

| Field | Detail |
| --- | --- |
| Why It Is Ambiguous | Could represent list price, discounted price, paid amount, subscription value, or currency-specific amount. |
| Resolved Meaning | Listed course price in the platform's reporting currency. |
| Business Interpretation | Used to analyze whether course cost affects conversion. |
| Suggested Better Name | `course_list_price` |
| Risk If Misunderstood | Conversion and revenue analysis may be wrong if discounts or subscription access are treated as list price. |

## 4. `preview_clicked`

| Field | Detail |
| --- | --- |
| Why It Is Ambiguous | Could mean the preview was shown, clicked, watched, completed, or simply available. |
| Resolved Meaning | Boolean flag showing whether the learner clicked or opened a course preview. |
| Business Interpretation | Measures learner interest after discovery. |
| Suggested Better Name | `course_preview_clicked_flag` |
| Risk If Misunderstood | Preview rate may be inflated if impressions are counted as clicks. |

## 5. `enrollment_status`

| Field | Detail |
| --- | --- |
| Why It Is Ambiguous | Status could refer to payment status, course completion status, account status, or enrollment state. |
| Resolved Meaning | Current state of the learner's enrollment record. |
| Business Interpretation | Used to identify active, pending, and cancelled enrollments. |
| Suggested Better Name | `course_enrollment_status` |
| Risk If Misunderstood | Cancelled or pending enrollments may be counted as successful conversions. |

## 6. `search_time`

| Field | Detail |
| --- | --- |
| Why It Is Ambiguous | Could refer to query submission time, result load time, server processing time, or local user time. |
| Resolved Meaning | Timestamp when the learner submitted a search query. |
| Business Interpretation | Supports search demand trends and funnel sequencing. |
| Suggested Better Name | `search_submitted_at` |
| Risk If Misunderstood | Funnel timing and daily search counts may shift if timezone or event meaning is unclear. |

## 7. `user_id`

| Field | Detail |
| --- | --- |
| Why It Is Ambiguous | Could identify a learner, instructor, admin, anonymous visitor, or account household. |
| Resolved Meaning | Unique identifier for a learner or platform user. |
| Business Interpretation | Links search, preview, and enrollment actions across the conversion funnel. |
| Suggested Better Name | `learner_user_id` |
| Risk If Misunderstood | Funnel reports may mix learner activity with staff or instructor activity. |
