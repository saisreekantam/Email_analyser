import React, { useState, useEffect } from 'react';
import { Bell, Mail, PieChart, Settings, LogOut, Search, Filter } from 'lucide-react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

const Dashboard = () => {
  const [emails, setEmails] = useState([]);
  const [metrics, setMetrics] = useState({
    total_emails: 0,
    categories: {},
    sentiment_distribution: {},
    priority_distribution: {},
    avg_response_time: null
  });
  const [loading, setLoading] = useState(true);

  // Mock data for demonstration
  useEffect(() => {
    setEmails([
      {
        email_id: '1',
        subject: 'Project Update Meeting',
        sender: 'john@example.com',
        category: 'Work',
        analysis_results: {
          priority_score: 0.8,
          sentiment: { label: 'positive', score: 0.9 },
          summary: 'Weekly project status update discussion',
          suggested_actions: ['Schedule meeting', 'Prepare report']
        }
      },
      {
        email_id: '2',
        subject: 'Invoice Payment Due',
        sender: 'billing@company.com',
        category: 'Finance',
        analysis_results: {
          priority_score: 0.9,
          sentiment: { label: 'neutral', score: 0.5 },
          summary: 'Payment reminder for recent services',
          suggested_actions: ['Review invoice', 'Process payment']
        }
      }
    ]);
    
    setMetrics({
      total_emails: 245,
      categories: { Work: 45, Finance: 28, Personal: 32 },
      sentiment_distribution: { positive: 120, neutral: 85, negative: 40 },
      priority_distribution: { high: 58, medium: 142, low: 45 },
      avg_response_time: 2.5
    });
    
    setLoading(false);
  }, []);

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <Mail className="h-8 w-8 text-blue-600" />
                <span className="ml-2 text-xl font-bold">Email Analyzer</span>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Bell className="h-6 w-6 text-gray-500" />
              <Settings className="h-6 w-6 text-gray-500" />
              <LogOut className="h-6 w-6 text-gray-500" />
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-gray-500">
                Total Emails
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.total_emails}</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-gray-500">
                Average Response Time
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {metrics.avg_response_time} hours
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-gray-500">
                High Priority
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {metrics.priority_distribution.high}
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-gray-500">
                Positive Sentiment
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {metrics.sentiment_distribution.positive}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Email List */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-4 py-5 border-b border-gray-200 sm:px-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Recent Emails
              </h3>
              <div className="flex space-x-3">
                <div className="relative">
                  <Search className="h-5 w-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search emails..."
                    className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50">
                  <Filter className="h-5 w-5 mr-2" />
                  Filter
                </button>
              </div>
            </div>
          </div>
          
          <ul className="divide-y divide-gray-200">
            {emails.map((email) => (
              <li key={email.email_id} className="px-4 py-4 sm:px-6 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center">
                      <p className="text-sm font-medium text-blue-600 truncate">
                        {email.subject}
                      </p>
                      <span className={`ml-2 px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        email.analysis_results.priority_score > 0.7 
                          ? 'bg-red-100 text-red-800'
                          : 'bg-green-100 text-green-800'
                      }`}>
                        {email.analysis_results.priority_score > 0.7 ? 'High Priority' : 'Normal'}
                      </span>
                    </div>
                    <div className="mt-1">
                      <p className="text-sm text-gray-500">
                        From: {email.sender}
                      </p>
                    </div>
                  </div>
                  <div className="flex-shrink-0 ml-4">
                    <span className={`px-3 py-1 text-xs rounded-full ${
                      email.category === 'Work' 
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-purple-100 text-purple-800'
                    }`}>
                      {email.category}
                    </span>
                  </div>
                </div>
                
                <div className="mt-2">
                  <p className="text-sm text-gray-600">
                    {email.analysis_results.summary}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {email.analysis_results.suggested_actions.map((action, index) => (
                      <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-gray-100 text-gray-800">
                        {action}
                      </span>
                    ))}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
