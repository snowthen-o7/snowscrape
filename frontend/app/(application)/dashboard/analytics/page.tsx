/**
 * Analytics Dashboard
 * Usage metrics, cost analysis, and performance insights
 */

'use client';

import { useState } from 'react';
import { AppLayout } from '@/components/layout';
import { PageHeader } from '@snowforge/ui';
import { StatCard } from '@snowforge/ui';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@snowforge/ui';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@snowforge/ui';
import { Badge } from '@snowforge/ui';
import { Button } from '@snowforge/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@snowforge/ui';
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

  // Analytics data (will be populated from API based on timeframe)
  const usageData7d: { date: string; jobs: number; apiCalls: number; dataVolume: number }[] = [];
  const costData: { date: string; cost: number }[] = [];
  const statusDistribution: { name: string; value: number }[] = [];
  const topJobs: {
    name: string;
    runs: number;
    successRate: number;
    avgRuntime: string;
    cost: string;
  }[] = [];
  const errorBreakdown: { type: string; count: number; percentage: number }[] = [];
  const performanceMetrics: { metric: string; value: string; change: number; trend: string }[] = [];

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
            value="0"
            icon={<Zap className="h-5 w-5" />}
          />
          <StatCard
            title="API Calls"
            value="0"
            icon={<Database className="h-5 w-5" />}
          />
          <StatCard
            title="Total Cost"
            value="$0.00"
            icon={<DollarSign className="h-5 w-5" />}
          />
          <StatCard
            title="Success Rate"
            value="0%"
            icon={<CheckCircle2 className="h-5 w-5" />}
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
                {topJobs.length > 0 ? (
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
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    <p>No job data available yet</p>
                    <p className="text-sm mt-1">Run some jobs to see performance metrics</p>
                  </div>
                )}
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
                        0 calls @ $0.0015/call
                      </p>
                    </div>
                    <p className="font-bold">$0.00</p>
                  </div>

                  <div className="flex items-center justify-between py-3 border-b border-border">
                    <div>
                      <p className="font-medium">JavaScript Rendering</p>
                      <p className="text-sm text-muted-foreground">
                        0 renders @ $0.02/render
                      </p>
                    </div>
                    <p className="font-bold">$0.00</p>
                  </div>

                  <div className="flex items-center justify-between py-3 border-b border-border">
                    <div>
                      <p className="font-medium">Proxy Usage</p>
                      <p className="text-sm text-muted-foreground">
                        0 requests @ $0.0001/request
                      </p>
                    </div>
                    <p className="font-bold">$0.00</p>
                  </div>

                  <div className="flex items-center justify-between py-3 border-b border-border">
                    <div>
                      <p className="font-medium">Data Storage</p>
                      <p className="text-sm text-muted-foreground">
                        0 GB @ $0.023/GB
                      </p>
                    </div>
                    <p className="font-bold">$0.00</p>
                  </div>

                  <div className="flex items-center justify-between pt-3">
                    <p className="text-lg font-bold">Total</p>
                    <p className="text-2xl font-bold text-accent-foreground">$0.00</p>
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
                  <p className="text-3xl font-bold">$0.00</p>
                  <div className="mt-2 flex items-center text-sm">
                    <span className="text-muted-foreground">No usage data yet</span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Projected Month End</CardTitle>
                  <CardDescription>Based on current usage</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold">$0.00</p>
                  <div className="mt-2 flex items-center text-sm">
                    <span className="text-muted-foreground">No usage data yet</span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Plan Limit</CardTitle>
                  <CardDescription>Current billing tier</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold">$0.00</p>
                  <div className="mt-2">
                    <Badge variant="outline">Free Plan</Badge>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Start using SnowScrape to see your spending
                  </p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Performance Tab */}
          <TabsContent value="performance" className="space-y-6">
            {performanceMetrics.length > 0 ? (
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
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <p>No performance metrics available yet</p>
                <p className="text-sm mt-1">Run some jobs to see performance data</p>
              </div>
            )}

            <Card>
              <CardHeader>
                <CardTitle>Performance Insights</CardTitle>
                <CardDescription>
                  Key recommendations to improve job performance
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12 text-muted-foreground">
                  <p>No insights available yet</p>
                  <p className="text-sm mt-1">Performance insights will appear here as you run jobs</p>
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
                <CardContent>
                  {errorBreakdown.length > 0 ? (
                    <div className="space-y-3">
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
                    </div>
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      <p>No error data available</p>
                      <p className="text-sm mt-1">Error statistics will appear when jobs fail</p>
                    </div>
                  )}
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
              <CardContent>
                <div className="text-center py-12 text-muted-foreground">
                  <p>No error resolution tips available</p>
                  <p className="text-sm mt-1">Troubleshooting guides will appear when errors occur</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
}
