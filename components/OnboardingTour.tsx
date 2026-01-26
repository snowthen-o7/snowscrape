/**
 * Onboarding Tour Component
 * Interactive tutorial for new users
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import {  } from '@snowforge/ui';
import {
  Rocket,
  Sparkles,
  FileText,
  Wand2,
  CheckCircle2,
  ArrowRight,
  X,
  Package,
} from 'lucide-react';
import { Progress } from '@/components/ui/progress';

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  icon: React.ReactElement;
  action?: {
    label: string;
    href: string;
  };
}

const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    id: 'welcome',
    title: 'Welcome to SnowScrape',
    description:
      'Your all-in-one web scraping platform. Extract data from any website without writing code.',
    icon: <Rocket className="h-12 w-12 text-accent-foreground" />,
  },
  {
    id: 'templates',
    title: 'Start with Templates',
    description:
      'Browse our library of pre-configured templates for popular websites like Amazon, LinkedIn, and more.',
    icon: <Package className="h-12 w-12 text-accent-foreground" />,
    action: {
      label: 'Browse Templates',
      href: '/dashboard/templates',
    },
  },
  {
    id: 'visual-builder',
    title: 'Visual Scraper Builder',
    description:
      'Point and click to build custom scrapers. No coding required - just select the data you want.',
    icon: <Wand2 className="h-12 w-12 text-accent-foreground" />,
    action: {
      label: 'Try Visual Builder',
      href: '/dashboard/jobs/new/visual',
    },
  },
  {
    id: 'analytics',
    title: 'Monitor Performance',
    description:
      'Track your jobs, analyze costs, and optimize performance with our comprehensive analytics dashboard.',
    icon: <FileText className="h-12 w-12 text-accent-foreground" />,
    action: {
      label: 'View Analytics',
      href: '/dashboard/analytics',
    },
  },
];

export function OnboardingTour() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);

  useEffect(() => {
    // Check if user has completed onboarding
    const hasCompletedOnboarding = localStorage.getItem('onboarding_completed');

    if (!hasCompletedOnboarding) {
      // Show onboarding after a brief delay
      setTimeout(() => {
        setIsOpen(true);
      }, 1000);
    }
  }, []);

  const handleNext = () => {
    const step = ONBOARDING_STEPS[currentStep];
    setCompletedSteps([...completedSteps, step.id]);

    if (currentStep < ONBOARDING_STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleComplete();
    }
  };

  const handleSkip = () => {
    localStorage.setItem('onboarding_completed', 'true');
    setIsOpen(false);
  };

  const handleComplete = () => {
    localStorage.setItem('onboarding_completed', 'true');
    setIsOpen(false);
  };

  const handleActionClick = (href: string) => {
    handleComplete();
    router.push(href);
  };

  const progress = ((currentStep + 1) / ONBOARDING_STEPS.length) * 100;
  const step = ONBOARDING_STEPS[currentStep];

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) handleSkip(); }}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <Badge variant="outline">
            Step {currentStep + 1} of {ONBOARDING_STEPS.length}
          </Badge>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Progress */}
          <Progress value={progress} className="h-2" />

          {/* Step Content */}
          <div className="text-center space-y-4">
            <div className="flex justify-center">{step.icon}</div>

            <div>
              <DialogTitle className="text-2xl mb-2">{step.title}</DialogTitle>
              <DialogDescription className="text-base">
                {step.description}
              </DialogDescription>
            </div>

            {step.action && (
              <div className="pt-4">
                <Button
                  onClick={() => handleActionClick(step.action!.href)}
                  className="w-full"
                >
                  {step.action.label}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            )}
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between pt-4">
            <Button variant="ghost" onClick={handleSkip}>
              Skip Tutorial
            </Button>

            <div className="flex gap-2">
              {currentStep > 0 && (
                <Button
                  variant="outline"
                  onClick={() => setCurrentStep(currentStep - 1)}
                >
                  Back
                </Button>
              )}
              <Button onClick={handleNext}>
                {currentStep === ONBOARDING_STEPS.length - 1 ? (
                  <>
                    Get Started
                    <CheckCircle2 className="ml-2 h-4 w-4" />
                  </>
                ) : (
                  <>
                    Next
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Quick Start Component - Shows on Dashboard
export function QuickStartGuide() {
  const router = useRouter();
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const isDismissed = localStorage.getItem('quickstart_dismissed');
    setDismissed(isDismissed === 'true');
  }, []);

  const handleDismiss = () => {
    localStorage.setItem('quickstart_dismissed', 'true');
    setDismissed(true);
  };

  if (dismissed) return null;

  return (
    <Card className="border-accent bg-gradient-to-r from-brand-accent/10 to-transparent">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <Sparkles className="h-8 w-8 text-accent-foreground" />
            <div>
              <CardTitle>Quick Start Guide</CardTitle>
              <CardDescription>
                Get started with SnowScrape in just a few minutes
              </CardDescription>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={handleDismiss}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-3">
          <Button
            variant="outline"
            className="h-auto flex-col items-start p-4 text-left"
            onClick={() => router.push('/dashboard/templates')}
          >
            <Package className="h-6 w-6 mb-2 text-accent-foreground" />
            <h4 className="font-semibold mb-1">Use a Template</h4>
            <p className="text-xs text-muted-foreground">
              Start with pre-built scrapers for popular sites
            </p>
          </Button>

          <Button
            variant="outline"
            className="h-auto flex-col items-start p-4 text-left"
            onClick={() => router.push('/dashboard/jobs/new/visual')}
          >
            <Wand2 className="h-6 w-6 mb-2 text-accent-foreground" />
            <h4 className="font-semibold mb-1">Visual Builder</h4>
            <p className="text-xs text-muted-foreground">
              Point and click to build custom scrapers
            </p>
          </Button>

          <Button
            variant="outline"
            className="h-auto flex-col items-start p-4 text-left"
            onClick={() => router.push('/dashboard')}
          >
            <FileText className="h-6 w-6 mb-2 text-accent-foreground" />
            <h4 className="font-semibold mb-1">Manual Setup</h4>
            <p className="text-xs text-muted-foreground">
              Configure your own scraping job from scratch
            </p>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// Success Celebration Component
export function JobSuccessCelebration({ jobName }: { jobName: string }) {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogContent className="sm:max-w-[500px]">
        <div className="text-center space-y-6 py-6">
          <div className="flex justify-center">
            <div className="h-20 w-20 rounded-full bg-green-100 flex items-center justify-center animate-bounce">
              <CheckCircle2 className="h-12 w-12 text-green-600" />
            </div>
          </div>

          <div>
            <DialogTitle className="text-3xl mb-3">
              Congratulations! 🎉
            </DialogTitle>
            <DialogDescription className="text-base">
              Your job <span className="font-semibold text-foreground">{jobName}</span> completed successfully! You've extracted your first data with SnowScrape.
            </DialogDescription>
          </div>

          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">What's next?</p>
            <div className="flex flex-col gap-2">
              <Button variant="outline" onClick={() => setIsOpen(false)}>
                View Results
              </Button>
              <Button variant="outline" onClick={() => setIsOpen(false)}>
                Create Another Job
              </Button>
            </div>
          </div>

          <Button variant="ghost" onClick={() => setIsOpen(false)} className="mt-4">
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
