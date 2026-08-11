# MonitorioRent cabinet override

This page extends the existing Monitorio Mini App and therefore overrides the
generic purple marketplace palette in the master recommendation.

## Existing Monitorio tokens

- Background: `#f4f6f9`
- Surface: `#ffffff`
- Soft surface: `#eef3f8`
- Primary: `#1667d9`
- Primary strong: `#0f4fb2`
- Text: `#111827`
- Muted text: `#687386`
- Border: `#d9e1ea`
- Success: `#168a55`
- Error: `#c24135`
- Radius: `14px`
- Font: system stack used by Monitorio

## Interaction rules

- The first question is a two-option role choice: renter or landlord.
- Both workflows remain available after onboarding through persistent bottom navigation.
- Listing submission is a three-step form with visible progress and automatic local drafts.
- All fields use visible labels, 48px controls, inline errors, and clear success feedback.
- The landlord is told that a submitted listing is pending review.
- The interface is mobile-first, supports dark mode, and respects reduced motion.
