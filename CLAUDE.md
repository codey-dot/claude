# Lead research rules for AI UGC outreach

## Goal
Find small-to-mid DTC brands likely to buy AI UGC video ads.

## Target markets
Australia, UAE, Saudi Arabia, Qatar, New Zealand (also US/UK/Canada if niche is uncrowded)

## Qualifying criteria (ALL must be true)
- Sells physical products online direct to consumers (own website/store)
- Niche: skincare, haircare, supplements, fitness, fashion accessories, home goods, pet products
- Website is live and working, with products and prices visible
- Has an Instagram account
- Shows signs of marketing activity (active socials, running ads, recent launches)

## Disqualify if
- Marketplace-only seller, dropshipping store with generic products, or an agency
- Large established brand (household name, retail chain)
- Website broken, parked, or "coming soon"

## Output
Append to leads.csv with columns:
brand, country, niche, website, instagram_handle, instagram_followers,
followers_source, contact_email, email_source, notes, status

## Accuracy rules
- Never guess or invent any value. If not confirmed, write "unverified".
- Record the URL where each email or follower count was found.
- Check leads.csv for duplicates before adding a brand.
- Work in batches of 20. Stop after each batch so I can review.
