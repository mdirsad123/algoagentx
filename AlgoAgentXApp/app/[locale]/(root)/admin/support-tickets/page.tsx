"use client"

import React, { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Separator } from "@/components/ui/separator"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { 
  MessageSquare, 
  Search, 
  RefreshCw, 
  Eye, 
  Filter, 
  Mail,
  Clock,
  User,
  Calendar,
  Tag
} from "lucide-react"
import { adminApi, SupportTicket } from "@/lib/api/admin"
import { toast } from "sonner"
import { parseApiError, formatErrorMessage } from "@/lib/api/error"
import { format } from "date-fns"

interface TicketMessage {
  id: string
  ticket_id: string
  sender_type: 'user' | 'admin'
  sender_name: string
  message: string
  created_at: string
}

export default function AdminSupportTicketsPage() {
  const [tickets, setTickets] = useState<SupportTicket[]>([])
  const [selectedTicket, setSelectedTicket] = useState<SupportTicket | null>(null)
  const [messages, setMessages] = useState<TicketMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [priorityFilter, setPriorityFilter] = useState<string>("")
  const [skip, setSkip] = useState(0)
  const [limit] = useState(20)
  const [total, setTotal] = useState(0)
  const [replyText, setReplyText] = useState("")

  const fetchTickets = async (newSkip?: number) => {
    try {
      setLoading(true)
      setError(null)
      const skipValue = newSkip !== undefined ? newSkip : skip
      const result = await adminApi.getSupportTickets(skipValue, limit, statusFilter || undefined)
      setTickets(result.items)
      setTotal(result.total)
      if (newSkip !== undefined) setSkip(newSkip)
    } catch (err) {
      console.error("Error fetching support tickets:", err)
      const errorInfo = parseApiError(err);
      const errorMessage = formatErrorMessage(errorInfo);
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const fetchTicketDetails = async (ticketId: string) => {
    try {
      setMessagesLoading(true)
      // For now, we'll use the ticket data directly since the API doesn't have a separate endpoint for messages
      // In a real implementation, you would fetch messages from: /api/v1/admin/support-tickets/{id}/messages
      const ticket = tickets.find(t => t.id === ticketId)
      if (ticket) {
        setSelectedTicket(ticket)
        // Create mock messages for demonstration
        const mockMessages: TicketMessage[] = [
          {
            id: "1",
            ticket_id: ticket.id,
            sender_type: "user",
            sender_name: ticket.user_email,
            message: ticket.message,
            created_at: ticket.created_at
          }
        ]
        setMessages(mockMessages)
      }
    } catch (err) {
      console.error("Error fetching ticket details:", err)
      toast.error("Failed to load ticket details")
    } finally {
      setMessagesLoading(false)
    }
  }

  const handleTicketSelect = (ticket: SupportTicket) => {
    setSelectedTicket(ticket)
    fetchTicketDetails(ticket.id)
  }

  const handleSearch = (searchValue: string) => {
    setSearch(searchValue)
    setSkip(0)
    setTimeout(() => {
      fetchTickets(0)
    }, 300)
  }

  const handleStatusFilter = (status: string) => {
    setStatusFilter(status)
    setSkip(0)
    fetchTickets(0)
  }

  const handlePriorityFilter = (priority: string) => {
    setPriorityFilter(priority)
    setSkip(0)
    fetchTickets(0)
  }

  const handleRefresh = () => {
    fetchTickets()
    if (selectedTicket) {
      fetchTicketDetails(selectedTicket.id)
    }
  }

  const handleStatusChange = async (ticketId: string, newStatus: string) => {
    try {
      await adminApi.updateTicketStatus(ticketId, newStatus)
      toast.success("Ticket status updated successfully")
      fetchTickets()
      if (selectedTicket?.id === ticketId) {
        setSelectedTicket(prev => prev ? { ...prev, status: newStatus } : null)
      }
    } catch (err) {
      console.error("Error updating ticket status:", err)
      toast.error("Failed to update ticket status")
    }
  }

  const handleReply = async () => {
    if (!replyText.trim() || !selectedTicket) return

    try {
      await adminApi.replyToTicket(selectedTicket.id, replyText)
      toast.success("Reply sent successfully")
      setReplyText("")
      fetchTicketDetails(selectedTicket.id)
      fetchTickets()
    } catch (err) {
      console.error("Error sending reply:", err)
      toast.error("Failed to send reply")
    }
  }

  useEffect(() => {
    fetchTickets()
  }, [])

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'OPEN': return "default"
      case 'IN_PROGRESS': return "secondary"
      case 'RESOLVED': return "outline"
      case 'CLOSED': return "destructive"
      default: return "default"
    }
  }

  const formatRelativeTime = (dateString: string) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy HH:mm')
    } catch {
      return dateString
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Support Tickets</h1>
          <p className="text-muted-foreground">Manage user support requests and conversations</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel - Tickets List */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <MessageSquare className="h-5 w-5" />
                    Tickets
                  </CardTitle>
                  <CardDescription>{total} total tickets</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Search className="h-4 w-4 text-gray-500" />
                  <Input
                    placeholder="Search tickets..."
                    value={search}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="w-48"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {/* Filters */}
              <div className="flex flex-wrap gap-2 mb-4">
                <Button
                  variant={statusFilter === "" ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleStatusFilter("")}
                >
                  All
                </Button>
                <Button
                  variant={statusFilter === "OPEN" ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleStatusFilter("OPEN")}
                  className="bg-green-500 hover:bg-green-600 text-white"
                >
                  Open
                </Button>
                <Button
                  variant={statusFilter === "IN_PROGRESS" ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleStatusFilter("IN_PROGRESS")}
                  className="bg-blue-500 hover:bg-blue-600 text-white"
                >
                  In Progress
                </Button>
                <Button
                  variant={statusFilter === "RESOLVED" ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleStatusFilter("RESOLVED")}
                  className="bg-yellow-500 hover:bg-yellow-600 text-white"
                >
                  Resolved
                </Button>
                <Button
                  variant={statusFilter === "CLOSED" ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleStatusFilter("CLOSED")}
                  className="bg-gray-500 hover:bg-gray-600 text-white"
                >
                  Closed
                </Button>
              </div>

              {/* Tickets List */}
              <div className="h-[600px] overflow-y-auto pr-4">
                {loading ? (
                  <div className="space-y-3">
                    {[...Array(5)].map((_, i) => (
                      <div key={i} className="flex space-x-3 p-3 rounded-lg border animate-pulse">
                        <div className="flex-1 space-y-2">
                          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                          <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : tickets.length === 0 ? (
                  <div className="text-center text-gray-500 py-8">
                    No tickets found
                  </div>
                ) : (
                  <div className="space-y-3">
                    {tickets.map((ticket) => (
                      <div
                        key={ticket.id}
                        className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                          selectedTicket?.id === ticket.id 
                            ? "border-primary bg-primary/5" 
                            : "hover:bg-accent"
                        }`}
                        onClick={() => handleTicketSelect(ticket)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge variant={getStatusBadgeVariant(ticket.status)}>
                                {ticket.status}
                              </Badge>
                              <span className="text-xs text-gray-500 flex items-center gap-1">
                                <User className="h-3 w-3" />
                                {ticket.user_email}
                              </span>
                            </div>
                            <h3 className="font-medium text-sm truncate">{ticket.title}</h3>
                            <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                              {ticket.message}
                            </p>
                            <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                              <span className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                {formatRelativeTime(ticket.created_at)}
                              </span>
                              <span className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {formatRelativeTime(ticket.updated_at)}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Pagination */}
              {total > 0 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <div className="text-sm text-gray-500">
                    Showing {skip + 1} - {Math.min(skip + limit, total)} of {total} tickets
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => fetchTickets(Math.max(0, skip - limit))}
                      disabled={skip === 0}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => fetchTickets(skip + limit)}
                      disabled={skip + limit >= total}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Panel - Ticket Details */}
        <div className="lg:col-span-2">
          {selectedTicket ? (
            <div className="space-y-6">
              {/* Ticket Header */}
              <Card>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-2">
                      <div className="flex items-center gap-3">
                        <CardTitle className="text-xl">{selectedTicket.title}</CardTitle>
                        <Badge variant={getStatusBadgeVariant(selectedTicket.status)}>
                          {selectedTicket.status}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-gray-600">
                        <span className="flex items-center gap-1">
                          <User className="h-4 w-4" />
                          {selectedTicket.user_email}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          Created: {formatRelativeTime(selectedTicket.created_at)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-4 w-4" />
                          Updated: {formatRelativeTime(selectedTicket.updated_at)}
                        </span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        onClick={() => handleStatusChange(selectedTicket.id, "OPEN")}
                        disabled={selectedTicket.status === "OPEN"}
                      >
                        Open
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => handleStatusChange(selectedTicket.id, "IN_PROGRESS")}
                        disabled={selectedTicket.status === "IN_PROGRESS"}
                      >
                        In Progress
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => handleStatusChange(selectedTicket.id, "RESOLVED")}
                        disabled={selectedTicket.status === "RESOLVED"}
                      >
                        Resolved
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => handleStatusChange(selectedTicket.id, "CLOSED")}
                        disabled={selectedTicket.status === "CLOSED"}
                      >
                        Closed
                      </Button>
                    </div>
                  </div>
                  <CardDescription>{selectedTicket.message}</CardDescription>
                </CardHeader>
              </Card>

              {/* Conversation Thread */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MessageSquare className="h-5 w-5" />
                    Conversation
                  </CardTitle>
                  <CardDescription>Messages between user and support team</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-[400px] overflow-y-auto pr-4">
                    {messagesLoading ? (
                      <div className="space-y-4">
                        {[...Array(3)].map((_, i) => (
                          <div key={i} className="flex space-x-3 p-3 rounded-lg border animate-pulse">
                            <div className="flex-1 space-y-2">
                              <div className="h-4 bg-gray-200 rounded w-1/4"></div>
                              <div className="h-3 bg-gray-200 rounded w-3/4"></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : messages.length === 0 ? (
                      <div className="text-center text-gray-500 py-8">
                        No messages yet. Be the first to reply!
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {messages.map((message) => (
                          <div
                            key={message.id}
                            className={`flex ${
                              message.sender_type === 'admin' ? 'justify-end' : 'justify-start'
                            }`}
                          >
                            <div
                              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                                message.sender_type === 'admin'
                                  ? 'bg-primary text-primary-foreground'
                                  : 'bg-gray-100 text-gray-900'
                              }`}
                            >
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs font-medium">
                                  {message.sender_name}
                                </span>
                                <span className="text-xs text-gray-500">
                                  {formatRelativeTime(message.created_at)}
                                </span>
                              </div>
                              <p className="text-sm">{message.message}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Reply Box */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Mail className="h-5 w-5" />
                    Reply to User
                  </CardTitle>
                  <CardDescription>Send a response to resolve this ticket</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Textarea
                    placeholder="Type your response here..."
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    className="min-h-[120px]"
                  />
                  <div className="flex justify-between items-center">
                    <div className="text-sm text-gray-500">
                      Admin response will be sent to {selectedTicket.user_email}
                    </div>
                    <Button 
                      onClick={handleReply}
                      disabled={!replyText.trim() || messagesLoading}
                    >
                      Send Reply
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card className="h-[700px] flex items-center justify-center">
              <div className="text-center space-y-4">
                <MessageSquare className="h-12 w-12 mx-auto text-gray-400" />
                <h3 className="text-lg font-semibold">Select a ticket</h3>
                <p className="text-gray-500">
                  Choose a ticket from the left panel to view details and respond
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}