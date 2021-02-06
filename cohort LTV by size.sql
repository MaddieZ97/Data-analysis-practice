With
-- 1. truncate date to month
monthly_agg as (
  Select
  	account_id as user_id, 
  	payment_usd as monthly_pay, 
  	date_trunc('month', payment_date) as payment_month
  From Transaction),

-- 2. aggregate all payments by user, count distinct payment month 
sum_month as (
  Select
  	user_id, 
  	sum(monthly_pay) as total_pay, 
  	count(distinct payment_month) as month_count
  From monthly_agg
  Group by user_id), 
  
 -- 3. calculate average monthly pay
 avg_month as (
   Select 
   	user_id, 
    total_pay/month_count as avg_monthly_pay
 From sum_month), 
 
 --4. categorize user into different sizes
categorized_user as (
   Select 
   	user_id, 
    case when avg_monthly_pay < 1000 then 'small'
         when avg_monthly_pay < 4000 then 'medium'
         else 'large' end as cohort
   From avg_month),
  
 -- 5. filter by size 
 filtered_user as (
    Select 
    	t.*
    from categorized_user c join 
    	 Transaction t
    On c.user_id = t.account_id
    where c.cohort = 'small'),           -- modify to 'small'/'medium'/'large'

  -- 6. aggregate payment by month for each customer, granularity -> user_id
   agg_month as (
	   	Select 
	   		account_id as user_id,
	   		date_trunc('month', payment_date) as payment_month,
	   		sum(payment_usd) as monthly_usd 
	   	From filtered_user
	   	Group by user_id, payment_month),

-- 7. get first month of payment for each customer, granularity -> user_id
   first_month as (
	   	Select 
	   		user_id, 
	   		date_trunc('month', min(payment_month)) as first_payment_month
	   	From agg_month 
	   	Group by user_id),

-- 8. append first month of payment to agg_month, filter out $0 payments, granularity -> user_id
   agg_month_withfirst as (
	   	Select 
	   		a.user_id, 
	   		a.payment_month,
	   		a.monthly_usd,
	   		f.first_payment_month
	   	From agg_month a 
	   	join first_month f
	   	on a.user_id = f.user_id
	   	Where a.monthly_usd != 0), 

-- 9. calculate initial cohort size, group customers by their first_payment_month
	agg_month_cohortsize as (
		Select 
			first_payment_month, 
            count(distinct user_id) as cohort_size_fixed
		From agg_month_withfirst
        Group by first_payment_month
		),

-- 10. aggregate to payment_month - first_payment_month granularity, trace the changing cohort_size by payment month
	agg_month_withsize as (
		Select
		    a1.first_payment_month, 
		    a1.payment_month, 
		    a2.cohort_size_fixed,
		    count(distinct a1.user_id) as cohort_size_changing,
		    sum(a1.monthly_usd) as cohort_usd
		From agg_month_withfirst a1
		join agg_month_cohortsize a2
		on a1.first_payment_month = a2.first_payment_month
	    Group by a1.first_payment_month, a1.payment_month, a2.cohort_size_fixed),

-- 11. get months since first payment month, append to each cohort group, granularity -> payment_month + first_payment_month
	agg_month_sincefirst as (
		Select 
			first_payment_month,
			payment_month,
			cohort_size_fixed,
			cohort_size_changing,
			cohort_usd,
			extract(YEAR from age(payment_month, first_payment_month)) * 12 + extract(MONTH from age(payment_month, first_payment_month)) as months_since_first
		From agg_month_withsize),

-- 12. calculate cumulative payments, granularity -> payment_month + first_payment_month
	cohort_sum as (
		Select 
			to_char(first_payment_month, 'yyyy-mm') as first_payment_month, 
			to_char(payment_month, 'yyyy-mm') as payment_month,
			months_since_first, 
			cohort_size_fixed,
			cohort_size_changing,
			round(cohort_usd::numeric, 2) as cohort_monthly_pay,
			round(sum(cohort_usd) over (partition by first_payment_month
								   order by payment_month)::numeric, 2) as cumm_sum  
		From agg_month_sincefirst
		order by 1,2,3,4,5,6)

Select * from cohort_sum; 




