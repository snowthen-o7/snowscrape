/**
 * Analytics Dashboard
 * Usage metrics, cost analysis, and performance insights
 */

'use client';

import { useState } from 'react';
import { AppLayout } from '@/components/layout';
import { PageHeader } from '@/components/PageHeader';
import { StatCard } from '@/components/StatCard';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {  } from '@snowforge/ui';
import { LineChart, BarChart, PieChart } from '@/components/charts';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Clock,
  CheckCircle2,
  XCircle,
  Database,
  Zap,
  AlertCircle,
  Download,
} from 'lucide-react';

export default function AnalyticsPage() {
  const [timeframe, setTimeframe] = useState('7d');

  // Sample data - in production, this would come from API based on timeframe
  const usageData7d = [
    { date: 'Jan 14', jobs: 15, apiCalls: 1200, dataVolume: 45 },
    { date: 'Jan 15', jobs: 22, apiCalls: 1890, dataVolume: 62 },
    { date: 'Jan 16', jobs: 28, apiCalls: 2100, dataVolume: 78 },
    { date: 'Jan 17', jobs: 19, apiCalls: 1750, dataVolume: 58 },
    { date: 'Jan 18', jobs: 31, apiCalls: 2300, dataVolume: 85 },
    { date: 'Jan 19', jobs: 34, apiCalls: 2800, dataVolume: 92 },
    { date: 'Jan 20', jobs: 38, apiCalls: 3200, dataVolume: 110 },
  ];

  const costData = [
    { date: 'Jan 14', cost: 2.5 },
    { date: 'Jan 15', cost: 3.2 },
    { date: 'Jan 16', cost: 3.8 },
    { date: 'Jan 17', cost: 2.9 },
    { date: 'Jan 18', cost: 4.1 },
    { date: 'Jan 19', cost: 4.5 },
    { date: 'Jan 20', cost: 5.2 },
  ];

  const statusDistribution = [
    { name: 'Success', value: 850 },
    { name: 'Failed', value: 120 },
    { name: 'Cancelled', value: 30 },
  ];

  const topJobs = [
    {
      name: 'Product Scraper - Amazon',
      runs: 450,
      successRate: 98.2,
      avgRuntime: '12s',
      cost: '$8.50',
    },
    {
      name: 'LinkedIn Profile Extractor',
      runs: 320,
      successRate: 94.1,
      avgRuntime: '18s',
      cost: '$6.20',
    },
    {
      name: 'Real Estate Listings',
      runs: 280,
      successRate: 96.8,
      avgRuntime: '15s',
      cost: '$5.80',
    },
    {
      name: 'News Article Aggregator',
      runs: 210,
      successRate: 99.5,
      avgRuntime: '8s',
      cost: '$3.40',
    },
    {
      name: 'E-commerce Price Monitor',
      runs: 180,
      successRate: 92.7,
      avgRuntime: '22s',
      cost: '$4.10',
    },
  ];

  const errorBreakdown = [
    { type: 'Timeout', count: 45, percentage: 37.5 },
    { type: 'Rate Limit', count: 32, percentage: 26.7 },
    { type: 'Invalid Selector', count: 24, percentage: 20.0 },
    { type: 'Connection Error', count: 12, percentage: 10.0 },
    { type: 'Other', count: 7, percentage: 5.8 },
  ];

  const performanceMetrics = [
    { metric: 'Average Runtime', value: '14.2s', change: -8.3, trend: 'up' },
    { metric: 'Success Rate', value: '95.8%', change: 2.1, trend: 'up' },
    { metric: 'Data Quality', value: '98.5%', change: 0.5, trend: 'up' },
    { metric: 'Avg Response Time', value: '1.2s', change: -15.2, trend: 'up' },
  ];

  return (
    <AppLayout>
      <div className="space-y-6 p-6">
        {/* Page Header */}
        <PageHeader
          title="Analytics"
          description="Usage metrics, cost analysis, and performance insights"
          actions={
            <div className="flex items-center gap-2">
              <Select value={timeframe} onValueChange={setTimeframe}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Select timeframe" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7d">Last 7 Days</SelectItem>
                  <SelectItem value="30d">Last 30 Days</SelectItem>
                  <SelectItem value="90d">Last 90 Days</SelectItem>
                  <SelectItem value="1y">Last Year</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="sm">
                <Download className="mr-2 h-4 w-4" />
                Export Report
              </Button>
            </div>
          }
        />

        {/* Overview Stats */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Total Jobs"
            value="187"
            icon={<Zap className="h-5 w-5" />}
            change={12}
            changeLabel="vs last period"
            trend="up"
          />
          <StatCard
            title="API Calls"
            value="15,240"
            icon={<Database className="h-5 w-5" />}
            change={18}
            changeLabel="vs last period"
            trend="up"
          />
          <StatCard
            title="Total Cost"
            value="$26.20"
            icon={<DollarSign className="h-5 w-5" />}
            change={-5}
            changeLabel="vs last period"
            trend="down"
          />
          <StatCard
            title="Success Rate"
            value="95.8%"
            icon={<CheckCircle2 className="h-5 w-5" />}
            change={2.1}
            changeLabel="vs last period"
            trend="up"
          />
        </div>

        {/* Main Analytics Tabs */}
        <Tabs defaultValue="usage" className="space-y-6">
          <TabsList>
            <TabsTrigger value="usage">Usage</TabsTrigger>
            <TabsTrigger value="cost">Cost Analysis</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="errors">Errors</TabsTrigger>
          </TabsList>

          {/* Usage Tab */}
          <TabsContent value="usage" className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Job Runs Over Time</CardTitle>
                  <CardDescription>
                    Number of jobs executed per day
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <LineChart
                    data={usageData7d}
                    xDataKey="date"
                    yDataKey="jobs"
                    lineColor="#00D9FF"
                    height={250}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>API Call Volume</CardTitle>
                  <CardDescription>
                    Total API calls made per day
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <LineChart
                    data={usageData7d}
                    xDataKey="date"
                    yDataKey="apiCalls"
                    lineColor="#22C55E"
                    height={250}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Data Volume (MB)</CardTitle>
                  <CardDescription>
                    Amount of data processed per day
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <BarChart
                    data={usageData7d}
                    xDataKey="date"
                    yDataKey="dataVolume"
                    barColor="#00D9FF"
                    height={250}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Job Status Distribution</CardTitle>
                  <CardDescription>
                    Breakdown of job outcomes
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <PieChart
                    data={statusDistribution}
                    dataKey="value"
                    nameKey="name"
                    colors={['#22C55E', '#EF4444', '#F59E0B']}
                    height={250}
                  />
                </CardContent>
              </Card>
            </div>

            {/* Top Jobs */}
            <Card>
              <CardHeader>
                <CardTitle>Top Performing Jobs</CardTitle>
                <CardDescription>
                  Most frequently run jobs in the selected period
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {topJobs.map((job, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between rounded-lg border border-border p-4"
                    >
                      <div className="flex items-center gap-4">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/10 text-accent-foreground font-bold">
                          {index + 1}
                        </div>
                        <div>
                          <p className="font-medium">{job.name}</p>
                          <p className="text-sm text-muted-foreground">
                            {job.runs} runs • {job.avgRuntime} avg runtime
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="text-right">
                          <p className="text-sm text-muted-foreground">Success Rate</p>
                          <p className="font-medium">{job.successRate}%</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-muted-foreground">Cost</p>
                          <p className="font-medium">{job.cost}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Cost Analysis Tab */}
          <TabsContent value="cost" className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Cost Trend</CardTitle>
                  <CardDescription>
                    Daily cost over the selected period
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <LineChart
                    data={costData}
                    xDataKey="date"
                    yDataKey="cost"
                    lineColor="#EF4444"
                    height={300}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Cost Breakdown</CardTitle>
                  <CardDescription>
                    Analysis of cost components
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between py-3 border-b border-border">
                    <div>
                      <p className="font-medium">API Calls</p>
                      <p className="text-sm text-muted-foreground">
                        15,240 calls @ $0.0015/call
                      </p>
                    </div>
                    <p className="font-bold">$22.86</p>
                  </div>

                  <div className="flex items-center justify-between py-3 border-b border-border">
                    <div>
                      <p className="font-medium">JavaScript Rendering</p>
                      <p className="text-sm text-muted-foreground">
                        120 renders @ $0.02/render
                      </p>
                    </div>
                    <p className="font-bold">$2.40</p>
                  </div>

                  <div className="flex items-center justify-between py-3 border-b border-border">
                    <div>
                      <p className="font-medium">Proxy Usage</p>
                      <p className="text-sm text-muted-foreground">
                        8,500 requests @ $0.0001/request
                      </p>
                    </div>
                    <p className="font-bold">$0.85</p>
                  </div>

                  <div className="flex items-center justify-between py-3 border-b border-border">
                    <div>
                      <p className="font-medium">Data Storage</p>
                      <p className="text-sm text-muted-foreground">
                        2.5 GB @ $0.023/GB
                      </p>
                    </div>
                    <p className="font-bold">$0.09</p>
                  </div>

                  <div className="flex items-center justify-between pt-3">
                    <p className="text-lg font-bold">Total</p>
                    <p className="text-2xl font-bold text-accent-foreground">$26.20</p>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
              <Card>
                <CardHeader>
                  <CardTitle>Current Month</CardTitle>
                  <CardDescription>Spending to date</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold">$26.20</p>
                  <div className="mt-2 flex items-center text-sm">
                    <TrendingDown className="mr-1 h-4 w-4 text-green-600" />
                    <span className="text-green-600">5% decrease</span>
                    <span className="text-muted-foreground ml-1">vs last month</span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Projected Month End</CardTitle>
                  <CardDescription>Based on current usage</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold">$42.50</p>
                  <div className="mt-2 flex items-center text-sm">
                    <TrendingUp className="mr-1 h-4 w-4 text-yellow-600" />
                    <span className="text-yellow-600">12% increase</span>
                    <span className="text-muted-foreground ml-1">vs last month</span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Plan Limit</CardTitle>
                  <CardDescription>Current billing tier</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold">$49.00</p>
                  <div className="mt-2">
                    <Badge variant="outline">Pro Plan</Badge>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">
                    $6.50 remaining before overage charges
                  </p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Performance Tab */}
          <TabsContent value="performance" className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
              {performanceMetrics.map((metric, index) => (
                <Card key={index}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium">
                      {metric.metric}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold">{metric.value}</p>
                    <div className="mt-2 flex items-center text-sm">
                      {metric.trend === 'up' ? (
                        <>
                          <TrendingUp className="mr-1 h-4 w-4 text-green-600" />
                          <span className="text-green-600">
                            {Math.abs(metric.change)}% improvement
                          </span>
                        </>
                      ) : (
                        <>
                          <TrendingDown className="mr-1 h-4 w-4 text-red-600" />
                          <span className="text-red-600">
                            {Math.abs(metric.change)}% decrease
                          </span>
                        </>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Performance Insights</CardTitle>
                <CardDescription>
                  Key recommendations to improve job performance
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border border-blue-500 bg-blue-900/10 p-4">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-blue-500 mt-0.5" />
                    <div>
                      <p className="font-medium">Runtime Optimization</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        Your average runtime decreased by 8.3% this period. Consider
                        applying similar optimization patterns to other jobs.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="rounded-lg border border-yellow-500 bg-yellow-900/10 p-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-yellow-500 mt-0.5" />
                    <div>
                      <p className="font-medium">Rate Limiting</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        32 jobs failed due to rate limiting. Consider adjusting your
                        rate_limit settings or adding delays between requests.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="rounded-lg border border-green-500 bg-green-900/10 p-4">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-green-500 mt-0.5" />
                    <div>
                      <p className="font-medium">High Success Rate</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        Your overall success rate of 95.8% is excellent. Keep up the
                        great job configuration!
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Errors Tab */}
          <TabsContent value="errors" className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Error Breakdown</CardTitle>
                  <CardDescription>
                    Most common error types
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <PieChart
                    data={errorBreakdown}
                    dataKey="count"
                    nameKey="type"
                    colors={['#EF4444', '#F59E0B', '#F97316', '#DC2626', '#7C2D12']}
                    height={250}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Error Statistics</CardTitle>
                  <CardDescription>
                    Detailed error analysis
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {errorBreakdown.map((error, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between rounded-lg border border-border p-3"
                    >
                      <div className="flex items-center gap-3">
                        <XCircle className="h-5 w-5 text-red-600" />
                        <div>
                          <p className="font-medium">{error.type}</p>
                          <p className="text-sm text-muted-foreground">
                            {error.count} occurrences
                          </p>
                        </div>
                      </div>
                      <Badge variant="outline">{error.percentage}%</Badge>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Error Resolution Guide</CardTitle>
                <CardDescription>
                  Common errors and how to fix them
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border border-border p-4">
                  <p className="font-medium mb-2">Timeout Errors (37.5%)</p>
                  <p className="text-sm text-muted-foreground mb-2">
                    Jobs timing out before completion. This usually indicates:
                  </p>
                  <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1 ml-2">
                    <li>Website is slow to respond</li>
                    <li>Too many concurrent requests</li>
                    <li>Need to enable JavaScript rendering</li>
                  </ul>
                  <Button variant="link" className="p-0 h-auto mt-2">
                    View Timeout Troubleshooting Guide →
                  </Button>
                </div>

                <div className="rounded-lg border border-border p-4">
                  <p className="font-medium mb-2">Rate Limit Errors (26.7%)</p>
                  <p className="text-sm text-muted-foreground mb-2">
                    Target website is blocking requests due to rate limiting:
                  </p>
                  <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1 ml-2">
                    <li>Reduce rate_limit setting in job configuration</li>
                    <li>Enable proxy rotation to distribute requests</li>
                    <li>Add random delays between requests</li>
                  </ul>
                  <Button variant="link" className="p-0 h-auto mt-2">
                    View Rate Limiting Best Practices →
                  </Button>
                </div>

                <div className="rounded-lg border border-border p-4">
                  <p className="font-medium mb-2">Invalid Selector Errors (20.0%)</p>
                  <p className="text-sm text-muted-foreground mb-2">
                    XPath or CSS selectors not matching expected elements:
                  </p>
                  <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1 ml-2">
                    <li>Website structure changed</li>
                    <li>JavaScript-rendered content (enable JS rendering)</li>
                    <li>Selector syntax error</li>
                  </ul>
                  <Button variant="link" className="p-0 h-auto mt-2">
                    View Selector Testing Guide →
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
}
