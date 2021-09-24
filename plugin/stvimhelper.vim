if exists('g:loaded_stvimhelper') || &compatible
  finish
endif

inoremap <C-L> <C-O>:call stvimhelper#InsertReview()<CR>

let g:loaded_stvimhelper = 1
