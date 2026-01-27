import { Hourglass } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ComingSoonProps {
  title: string;
  description?: string;
  phase?: string;
  className?: string;
}

export const ComingSoon: React.FC<ComingSoonProps> = ({ title, description, phase, className }) => {
  return (
    <div className={cn('flex items-center justify-center min-h-[60vh]', className)}>
      <div className="text-center">
        <div className="flex justify-center mb-6">
          <Hourglass className="h-16 w-16 text-muted-foreground animate-pulse" />
        </div>

        <h1 className="text-3xl font-bold text-foreground mb-3">{title}</h1>

        {description && <p className="text-muted-foreground mb-2">{description}</p>}

        {phase && (
          <p className="text-sm text-muted-foreground/70">
            Phase de développement: <span className="font-medium">{phase}</span>
          </p>
        )}
      </div>
    </div>
  );
};
