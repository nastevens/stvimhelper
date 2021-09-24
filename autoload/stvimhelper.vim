if exists('g:autoload_stvimhelper') || &compatible
  finish
endif

function! stvimhelper#InsertReview() abort
  " Read contents of clipboard register with @+
  let url = @+

  " Hand off to helper script, which returns text to insert
  silent let text = trim(system('stvimhelper review ' . shellescape(url)))
  if v:shell_error
    echo text
    return ''
  endif

  " Insert it
  let col = col('.')
  let line = getline('.')
  let lineno = line('.')
  let newline = strpart(line, 0, col) . text . strpart(line, col)
  call setline(lineno, newline)
  call cursor(lineno, col + strlen(text))
endfunction

let g:autoload_stvimhelper = 1
