# Add Logo to Login Page

## Objective
Add the F&D logo (`FD_logotipo.svg`) above the "Order Processing – Text Orders" title on the login page, matching the style shown in the F&D Master Data app.

## Current State
- Logo file exists at: `frontend/public/FD_logotipo.svg`
- Login page component: `frontend/src/components/LoginPage.tsx`
- Header section is at lines 64-86, containing the title and "Enterprise Portal" subtitle

## Implementation

### File to Modify
- [LoginPage.tsx](frontend/src/components/LoginPage.tsx)

### Changes
Add an `<img>` element above the `<h1>` tag in the Header Section (around line 65):

```tsx
{/* Header Section */}
<div style={{ textAlign: 'center', marginBottom: '24px' }}>
  {/* Logo - ADD THIS */}
  <img
    src="/FD_logotipo.svg"
    alt="F&D In Shower Tray"
    style={{
      width: '180px',
      height: 'auto',
      marginBottom: '16px',
    }}
  />
  <h1 ... >
    Order Processing – Text Orders
  </h1>
  ...
</div>
```

### Styling Notes
- Width: ~180px (can be adjusted to match Master Data app proportions)
- Centered via parent `textAlign: 'center'`
- Bottom margin of 16px to create spacing between logo and title
- The SVG is an F&D branded logo with gradient teal/blue colors

## Verification
1. Start the frontend dev server: `cd frontend && npm run dev`
2. Navigate to http://localhost:5173/login
3. Verify the logo appears above the title
4. Compare with the F&D Master Data app screenshot for visual consistency
5. Check responsive behavior on different screen sizes
