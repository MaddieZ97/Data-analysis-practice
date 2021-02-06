-- Transaction data breakdown 
-- account_id: id of the customer, 1158 customers in total 
-- payment_id: id of the payment, one customer can make multiple payments 
-- payment_usd: amount of each payment, note there are $0 payments, one customer can pay $0 for a certain month 
-- payment_date: date of the payment, customer doesn't pay multiple times on the same day, one user - one paymentdate - one payment 

With
-- 1. aggregate payment by month for each customer, granularity -> user_id
   agg_month as (
	   	Select 
	   		account_id as user_id,
	   		date_trunc('month', payment_date) as payment_month,
	   		sum(payment_usd) as monthly_usd 
	   	From Transaction
	   	Group by user_id, payment_month),

-- 2. get first month of payment for each customer, granularity -> user_id
   first_month as (
	   	Select 
	   		user_id, 
	   		date_trunc('month', min(payment_month)) as first_payment_month
	   	From agg_month 
	   	Group by user_id),

-- 3. append first month of payment to agg_month, filter out $0 payments, granularity -> user_id
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

-- 4. calculate initial cohort size, group customers by their first_payment_month
	agg_month_cohortsize as (
		Select 
			first_payment_month, 
            count(distinct user_id) as cohort_size_fixed
		From agg_month_withfirst
        Group by first_payment_month
		),

-- 5. aggregate to payment_month - first_payment_month granularity, trace the changing cohort_size by payment month
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

-- 6. get months since first payment month, append to each cohort group, granularity -> payment_month + first_payment_month
	agg_month_sincefirst as (
		Select 
			first_payment_month,
			payment_month,
			cohort_size_fixed,
			cohort_size_changing,
			cohort_usd,
			extract(YEAR from age(payment_month, first_payment_month)) * 12 + extract(MONTH from age(payment_month, first_payment_month)) as months_since_first
		From agg_month_withsize),

-- 7. calculate cumulative payments, granularity -> payment_month + first_payment_month
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




