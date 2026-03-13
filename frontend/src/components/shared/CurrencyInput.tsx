import React from 'react'
import { formatCurrency, parseCurrency } from '@/lib/utils'

interface CurrencyInputProps {
  value: number
  onChange: (value: number) => void
  placeholder?: string
  disabled?: boolean
  label?: string
  error?: string
  className?: string
  emptyWhenZero?: boolean
}

const CurrencyInput: React.FC<CurrencyInputProps> = ({
  value,
  onChange,
  placeholder = 'Digite o valor',
  disabled = false,
  label,
  error,
  className = '',
  emptyWhenZero = true,
}) => {
  const formatDisplay = React.useCallback(
    (nextValue: number) => {
      if (emptyWhenZero && (!nextValue || Number(nextValue) === 0)) {
        return ''
      }
      return formatCurrency(nextValue)
    },
    [emptyWhenZero],
  )

  const [displayValue, setDisplayValue] = React.useState(() => formatDisplay(value))

  React.useEffect(() => {
    setDisplayValue(formatDisplay(value))
  }, [formatDisplay, value])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const rawDigits = e.target.value.replace(/\D/g, '')

    if (rawDigits.length === 0) {
      setDisplayValue('')
      onChange(0)
      return
    }

    const numValue = parseCurrency(rawDigits)
    setDisplayValue(formatCurrency(numValue))
    onChange(numValue)
  }

  const handleBlur = () => {
    if (displayValue === '') {
      setDisplayValue(formatDisplay(0))
      onChange(0)
    }
  }

  return (
    <div className="w-full">
      {label && <label className="block text-sm font-medium text-slate-700 mb-2">{label}</label>}
      <input
        type="text"
        value={displayValue}
        onChange={handleChange}
        onBlur={handleBlur}
        placeholder={placeholder}
        disabled={disabled}
        inputMode="numeric"
        className={`input-field ${error ? 'border-danger' : ''} ${className}`.trim()}
      />
      {error && <p className="text-danger text-sm mt-1">{error}</p>}
    </div>
  )
}

export default CurrencyInput
