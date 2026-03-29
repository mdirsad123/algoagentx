import * as React from "react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "./enhanced-card"
import { Button } from "./enhanced-button"
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuLabel } from "./enhanced-dropdown"
import { ChevronDown } from "lucide-react"

export default function TestEnhancedComponents() {
  const [dropdownOpen, setDropdownOpen] = React.useState(false)

  return (
    <div className="p-8 space-y-8">
      <h1 className="text-3xl font-bold text-neutral-900 mb-8">Enhanced Components Test</h1>
      
      {/* Test Enhanced Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card variant="default">
          <CardHeader>
            <CardTitle>Default Card</CardTitle>
            <CardDescription>A standard card with default styling</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-neutral-600">This is the card content area with proper spacing and typography.</p>
          </CardContent>
          <CardFooter>
            <Button variant="default">Action</Button>
          </CardFooter>
        </Card>

        <Card variant="elevated">
          <CardHeader>
            <CardTitle>Elevated Card</CardTitle>
            <CardDescription>A card with enhanced shadow and hover effects</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-neutral-600">This card has a subtle shadow that elevates it from the background.</p>
          </CardContent>
          <CardFooter>
            <Button variant="outline">Secondary Action</Button>
          </CardFooter>
        </Card>

        <Card variant="outlined">
          <CardHeader>
            <CardTitle>Outlined Card</CardTitle>
            <CardDescription>A card with a bold primary border</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-neutral-600">This card features a prominent border that draws attention.</p>
          </CardContent>
          <CardFooter>
            <Button variant="destructive">Danger Action</Button>
          </CardFooter>
        </Card>
      </div>

      {/* Test Enhanced Buttons */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold text-neutral-900">Button Variants</h2>
        <div className="flex flex-wrap gap-4">
          <Button variant="default">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="link">Link</Button>
        </div>
        
        <div className="flex flex-wrap gap-4">
          <Button size="sm">Small</Button>
          <Button size="default">Default</Button>
          <Button size="lg">Large</Button>
          <Button size="icon">
            <ChevronDown className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Test Enhanced Dropdown */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold text-neutral-900">Dropdown Menu</h2>
        <div className="flex gap-4">
          <DropdownMenu open={dropdownOpen} onOpenChange={setDropdownOpen}>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                Language
                <ChevronDown className="ml-2 h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Language Selection</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={() => setDropdownOpen(false)}>
                English
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => setDropdownOpen(false)}>
                Spanish
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => setDropdownOpen(false)}>
                French
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => setDropdownOpen(false)}>
                German
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Button 
            variant="outline" 
            onClick={() => setDropdownOpen(!dropdownOpen)}
          >
            Toggle Dropdown
          </Button>
        </div>
      </div>

      {/* Test AutoClose Dropdown */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold text-neutral-900">AutoClose Dropdown</h2>
        <div className="flex gap-4">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                AutoClose Menu
                <ChevronDown className="ml-2 h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>AutoClose Features</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem>Closes on outside click</DropdownMenuItem>
              <DropdownMenuItem>Closes on ESC key</DropdownMenuItem>
              <DropdownMenuItem>Closes on route change</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </div>
  )
}