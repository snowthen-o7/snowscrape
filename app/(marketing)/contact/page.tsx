/**
 * Contact Page
 * Multiple contact methods and inquiry form
 */

'use client';

import { MarketingLayout } from '@/components/layout/MarketingLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Mail, MessageCircle, Phone, MapPin, Send } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'react-toastify';

export default function Contact() {
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    company: '',
    subject: '',
    message: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Simulate form submission
    await new Promise((resolve) => setTimeout(resolve, 1500));

    toast.success('Message sent! We\'ll get back to you within 24 hours.');
    setFormData({
      firstName: '',
      lastName: '',
      email: '',
      company: '',
      subject: '',
      message: '',
    });
    setIsSubmitting(false);
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <MarketingLayout>
      {/* Hero */}
      <section className="bg-gradient-to-br from-brand-primary to-brand-primary/90 py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
              Get in touch
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-300">
              Have a question about SnowScrape? We're here to help. Reach out through any
              of our channels below.
            </p>
          </div>
        </div>
      </section>

      {/* Contact Methods & Form */}
      <section className="bg-background py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-16 lg:grid-cols-2">
            {/* Contact Info */}
            <div>
              <h2 className="text-2xl font-bold text-foreground">
                Contact Information
              </h2>
              <p className="mt-4 text-muted-foreground">
                Choose your preferred method of communication. Our team is available
                24/7 to assist you.
              </p>

              <div className="mt-12 space-y-6">
                {/* Email */}
                <div className="flex gap-4 rounded-lg border border-border bg-card p-6 transition-all hover:border-brand-accent/50">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-accent/10">
                    <Mail className="h-6 w-6 text-brand-accent" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-foreground">Email</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Our team typically responds within 24 hours
                    </p>
                    <a
                      href="mailto:support@snowscrape.com"
                      className="mt-2 inline-block text-sm font-medium text-brand-accent hover:text-brand-accent/80"
                    >
                      support@snowscrape.com
                    </a>
                  </div>
                </div>

                {/* Live Chat */}
                <div className="flex gap-4 rounded-lg border border-border bg-card p-6 transition-all hover:border-brand-accent/50">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-accent/10">
                    <MessageCircle className="h-6 w-6 text-brand-accent" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-foreground">Live Chat</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Chat with our support team in real-time
                    </p>
                    <button className="mt-2 text-sm font-medium text-brand-accent hover:text-brand-accent/80">
                      Start a chat →
                    </button>
                  </div>
                </div>

                {/* Phone */}
                <div className="flex gap-4 rounded-lg border border-border bg-card p-6 transition-all hover:border-brand-accent/50">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-accent/10">
                    <Phone className="h-6 w-6 text-brand-accent" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-foreground">
                      Phone <span className="text-xs text-muted-foreground">(Business & Enterprise)</span>
                    </h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Available Mon-Fri, 9am-5pm PST
                    </p>
                    <a
                      href="tel:+1-555-123-4567"
                      className="mt-2 inline-block text-sm font-medium text-brand-accent hover:text-brand-accent/80"
                    >
                      +1 (555) 123-4567
                    </a>
                  </div>
                </div>

                {/* Office */}
                <div className="flex gap-4 rounded-lg border border-border bg-card p-6 transition-all hover:border-brand-accent/50">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-accent/10">
                    <MapPin className="h-6 w-6 text-brand-accent" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-foreground">Office</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      123 Tech Street
                      <br />
                      San Francisco, CA 94105
                      <br />
                      United States
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Contact Form */}
            <div>
              <div className="rounded-2xl border border-border bg-card p-8">
                <h2 className="text-2xl font-bold text-foreground">
                  Send us a message
                </h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  Fill out the form below and we'll get back to you as soon as possible.
                </p>

                <form onSubmit={handleSubmit} className="mt-8 space-y-6">
                  {/* Name */}
                  <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                    <div>
                      <Label htmlFor="firstName">First Name *</Label>
                      <Input
                        id="firstName"
                        name="firstName"
                        type="text"
                        required
                        value={formData.firstName}
                        onChange={handleChange}
                        className="mt-2"
                        placeholder="John"
                      />
                    </div>
                    <div>
                      <Label htmlFor="lastName">Last Name *</Label>
                      <Input
                        id="lastName"
                        name="lastName"
                        type="text"
                        required
                        value={formData.lastName}
                        onChange={handleChange}
                        className="mt-2"
                        placeholder="Doe"
                      />
                    </div>
                  </div>

                  {/* Email */}
                  <div>
                    <Label htmlFor="email">Email *</Label>
                    <Input
                      id="email"
                      name="email"
                      type="email"
                      required
                      value={formData.email}
                      onChange={handleChange}
                      className="mt-2"
                      placeholder="john@example.com"
                    />
                  </div>

                  {/* Company */}
                  <div>
                    <Label htmlFor="company">Company</Label>
                    <Input
                      id="company"
                      name="company"
                      type="text"
                      value={formData.company}
                      onChange={handleChange}
                      className="mt-2"
                      placeholder="Acme Inc."
                    />
                  </div>

                  {/* Subject */}
                  <div>
                    <Label htmlFor="subject">Subject *</Label>
                    <Select
                      required
                      value={formData.subject}
                      onValueChange={(value) =>
                        setFormData({ ...formData, subject: value })
                      }
                    >
                      <SelectTrigger className="mt-2">
                        <SelectValue placeholder="Select a subject" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="general">General Inquiry</SelectItem>
                        <SelectItem value="support">Technical Support</SelectItem>
                        <SelectItem value="sales">Sales Question</SelectItem>
                        <SelectItem value="billing">Billing Issue</SelectItem>
                        <SelectItem value="feature">Feature Request</SelectItem>
                        <SelectItem value="partnership">Partnership Opportunity</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Message */}
                  <div>
                    <Label htmlFor="message">Message *</Label>
                    <textarea
                      id="message"
                      name="message"
                      required
                      rows={5}
                      value={formData.message}
                      onChange={handleChange}
                      className="mt-2 flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      placeholder="Tell us more about your inquiry..."
                    />
                  </div>

                  {/* Submit Button */}
                  <Button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full bg-brand-accent text-brand-primary hover:bg-brand-accent/90"
                    size="lg"
                  >
                    {isSubmitting ? (
                      'Sending...'
                    ) : (
                      <>
                        Send Message
                        <Send className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>

                  <p className="text-xs text-muted-foreground">
                    By submitting this form, you agree to our Privacy Policy and Terms of Service.
                  </p>
                </form>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="bg-muted/30 py-24 sm:py-32">
        <div className="mx-auto max-w-3xl px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Common questions
            </h2>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              Quick answers to questions you may have
            </p>
          </div>

          <Accordion type="single" collapsible className="mt-16">
            <AccordionItem value="item-1">
              <AccordionTrigger>What are your support hours?</AccordionTrigger>
              <AccordionContent>
                Our support team is available 24/7 for email and live chat. Phone support
                is available Monday-Friday, 9am-5pm PST for Business and Enterprise customers.
                All inquiries are typically responded to within 24 hours.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-2">
              <AccordionTrigger>Do you offer dedicated support?</AccordionTrigger>
              <AccordionContent>
                Yes! Enterprise customers receive a dedicated account manager and priority
                support with custom SLA guarantees. Business customers get priority email
                and phone support. Contact our sales team to learn more.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-3">
              <AccordionTrigger>Can I schedule a demo?</AccordionTrigger>
              <AccordionContent>
                Absolutely! We offer personalized demos for teams and businesses. Select
                "Sales Question" as your subject in the contact form above, and our team
                will reach out to schedule a convenient time for a live demo.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-4">
              <AccordionTrigger>How do I report a bug or request a feature?</AccordionTrigger>
              <AccordionContent>
                You can report bugs through our email support or live chat. For feature
                requests, select "Feature Request" in the contact form above. We review all
                feature requests and prioritize based on customer feedback and usage patterns.
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      </section>
    </MarketingLayout>
  );
}
