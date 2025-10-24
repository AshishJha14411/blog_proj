// components/common/Footer.tsx
export default function Footer() {
  return (
    <footer className="border-t p-8 text-center text-text-light">
      <p>&copy; {new Date().getFullYear()} Pixel Point. All rights reserved.</p>
    </footer>
  );
}