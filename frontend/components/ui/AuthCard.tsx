// components/ui/AuthCard.tsx
interface AuthCardProps {
  title: string;
  children: React.ReactNode;
}

export default function AuthCard({ title, children }: AuthCardProps) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="w-full max-w-md rounded-lg bg-background-alt p-8 shadow-md">
        <h2 className="mb-6 text-center text-3xl font-bold text-text">
          {title}
        </h2>
        {children}
      </div>
    </div>
  );
}
